from compas_rui.values import BoolValue
from compas_rui.values import FloatValue
from compas_rui.values import Settings

SETTINGS = {
    "Session": Settings(
        {
            "autosave.events": BoolValue(True),
        }
    ),
    "Masonry": Settings({}),
    "Model": Settings({}),
    "CRA": Settings({}),
}
