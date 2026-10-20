import importlib
import traceback

import adsk.core

from .core import builders, layout, profile
from .ui import command

_app = adsk.core.Application.get()


def run(context):
    try:
        importlib.reload(profile)
        importlib.reload(layout)
        importlib.reload(builders)
        importlib.reload(command)
        command.start()
    except Exception:
        _app.userInterface.messageBox('Failed to start:\n{}'.format(traceback.format_exc()))


def stop(context):
    try:
        command.stop()
    except Exception:
        _app.userInterface.messageBox('Failed to stop:\n{}'.format(traceback.format_exc()))

