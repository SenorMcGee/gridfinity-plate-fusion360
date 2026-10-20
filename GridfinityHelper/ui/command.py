import traceback

import adsk.core
import adsk.fusion

from ..core import builders, layout as L
from ..core import profile as P

CMD_ID = 'gridfinityHelperCmd'
_app = adsk.core.Application.get()
_ui = _app.userInterface
_handlers = []

MFG = ['3D Printed', 'Laser Cut', 'CNC']
MODES = ['Center & pad leftover', 'Cut partial cells']
ALIGNS = ['Center', 'Start (left/bottom)', 'End (right/top)']
_ALIGN_MAP = {ALIGNS[0]: L.CENTER, ALIGNS[1]: L.START, ALIGNS[2]: L.END}


def _mm(inputs, id_):
    return inputs.itemById(id_).value * 10.0  # internal cm -> mm


class _Changed(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            if args.input.id == 'summary':
                return
            _refresh(args.input.parentCommand.commandInputs)
        except Exception:
            _ui.messageBox(traceback.format_exc())


def _dropdown(inputs, id_, name, items):
    dd = inputs.addDropDownCommandInput(
        id_, name, adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, it in enumerate(items):
        dd.listItems.add(it, i == 0)
    return dd


def _compute(inputs):
    mode = L.PAD if inputs.itemById('mode').selectedItem.name == MODES[0] else L.PARTIAL
    ax = _ALIGN_MAP[inputs.itemById('alignX').selectedItem.name]
    ay = _ALIGN_MAP[inputs.itemById('alignY').selectedItem.name]
    split_on = inputs.itemById('splitBed').value
    max_l = _mm(inputs, 'maxLength') if split_on else 0.0
    max_w = _mm(inputs, 'maxWidth') if split_on else 0.0
    return L.compute_layout(_mm(inputs, 'length'), _mm(inputs, 'width'),
                            _mm(inputs, 'pitch'), mode, ax, ay,
                            _mm(inputs, 'minPartial'),
                            max_length=max_l, max_width=max_w)


def _refresh(inputs):
    mfg = inputs.itemById('mfg').selectedItem.name
    inputs.itemById('grpPrint').isVisible = mfg == MFG[0]
    inputs.itemById('grpLaser').isVisible = mfg == MFG[1]
    inputs.itemById('grpCnc').isVisible = mfg == MFG[2]
    split_on = inputs.itemById('splitBed').value
    inputs.itemById('maxLength').isEnabled = split_on
    inputs.itemById('maxWidth').isEnabled = split_on
    inputs.itemById('tileGap').isEnabled = split_on
    try:
        lay = _compute(inputs)
        partials = sum(1 for c in lay.cells if c.partial)
        tile_line = '1 tile (no split)'
        if len(lay.tiles) > 1:
            sizes = sorted({'{:.0f}x{:.0f}'.format(t.width, t.height) for t in lay.tiles})
            tile_line = '{} x {} = {} tiles ({} mm)'.format(
                lay.tiles_x, lay.tiles_y, len(lay.tiles), ', '.join(sizes))
        inputs.itemById('summary').text = (
            '{} x {} cells ({} partial)\n'
            'Padding X: {:.1f} / {:.1f} mm | Y: {:.1f} / {:.1f} mm\n'
            'Tiles: {}').format(
                lay.cols, lay.rows, partials, *lay.pad_x, *lay.pad_y, tile_line)
    except Exception:
        inputs.itemById('summary').text = 'Invalid dimensions'


class _Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            vi = adsk.core.ValueInput.createByString
            inputs.addValueInput('length', 'Length', 'mm', vi('210 mm'))
            inputs.addValueInput('width', 'Width', 'mm', vi('126 mm'))
            inputs.addValueInput('pitch', 'Grid pitch', 'mm', vi('42 mm'))
            _dropdown(inputs, 'mfg', 'Manufacturing', MFG)
            _dropdown(inputs, 'mode', 'Dead space', MODES)
            _dropdown(inputs, 'alignX', 'Align X', ALIGNS)
            _dropdown(inputs, 'alignY', 'Align Y', ALIGNS)
            inputs.addValueInput('minPartial', 'Min partial cell', 'mm', vi('5 mm'))

            g_bed = inputs.addGroupCommandInput('grpBed', 'Machine bed / work area limit').children
            g_bed.addBoolValueInput('splitBed', 'Split to fit bed size', True, '', False)
            g_bed.addValueInput('maxLength', 'Max bed X (length)', 'mm', vi('256 mm'))
            g_bed.addValueInput('maxWidth', 'Max bed Y (width)', 'mm', vi('256 mm'))
            g_bed.addValueInput('tileGap', 'Visual gap between tiles', 'mm', vi('5 mm'))

            g = inputs.addGroupCommandInput('grpPrint', '3D print options').children
            g.addBoolValueInput('magnets', 'Magnet holes', True, '', True)
            g.addValueInput('floor', 'Floor thickness', 'mm', vi('0 mm'))
            g = inputs.addGroupCommandInput('grpLaser', 'Laser options').children
            g.addValueInput('thickness', 'Material thickness', 'mm', vi('3 mm'))
            g.addValueInput('kerf', 'Kerf', 'mm', vi('0.15 mm'))
            g.addValueInput('laserRadius', 'Corner radius', 'mm', vi('1.6 mm'))
            g = inputs.addGroupCommandInput('grpCnc', 'CNC options').children
            g.addValueInput('stock', 'Stock thickness', 'mm', vi('12 mm'))
            g.addValueInput('tool', 'Tool diameter', 'mm', vi('3 mm'))
            inputs.addTextBoxCommandInput('summary', 'Layout', '', 4, True)
            _refresh(inputs)

            h = _Changed(); cmd.inputChanged.add(h); _handlers.append(h)
            h = _Execute(); cmd.execute.add(h); _handlers.append(h)
        except Exception:
            _ui.messageBox(traceback.format_exc())


class _Execute(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            i = args.command.commandInputs
            design = adsk.fusion.Design.cast(_app.activeProduct)
            if not design:
                _ui.messageBox('Open a Design first.')
                return
            lay = _compute(i)
            length, width, pitch = _mm(i, 'length'), _mm(i, 'width'), _mm(i, 'pitch')
            tile_gap = _mm(i, 'tileGap') if i.itemById('splitBed').value else 0.0
            mfg = i.itemById('mfg').selectedItem.name
            if mfg == MFG[0]:
                builders.build_printed(design, lay, length, width, pitch,
                                       _mm(i, 'floor'), i.itemById('magnets').value,
                                       tile_gap=tile_gap)
            elif mfg == MFG[1]:
                builders.build_laser(design, lay, length, width, pitch, _mm(i, 'thickness'),
                                     _mm(i, 'kerf'), _mm(i, 'laserRadius'),
                                     tile_gap=tile_gap)
            else:
                builders.build_cnc(design, lay, length, width, pitch, _mm(i, 'stock'),
                                   _mm(i, 'tool'), tile_gap=tile_gap)
        except Exception:
            _ui.messageBox(traceback.format_exc())


def start():
    defn = _ui.commandDefinitions.itemById(CMD_ID)
    if defn:
        defn.deleteMe()
    defn = _ui.commandDefinitions.addButtonDefinition(
        CMD_ID, 'Gridfinity Plate', 'Generate a Gridfinity plate')
    h = _Created(); defn.commandCreated.add(h); _handlers.append(h)
    panel = _ui.allToolbarPanels.itemById('SolidCreatePanel')
    ctrl = panel.controls.addCommand(defn)
    ctrl.isPromoted = True


def stop():
    panel = _ui.allToolbarPanels.itemById('SolidCreatePanel')
    ctrl = panel.controls.itemById(CMD_ID)
    if ctrl:
        ctrl.deleteMe()
    defn = _ui.commandDefinitions.itemById(CMD_ID)
    if defn:
        defn.deleteMe()
