from __future__ import annotations

from PyQt6.QtWidgets import QTableView
from vapoursynth import FrameProps
from vstools import ChromaLocation, ColorRange, FieldBased, Matrix, Primaries, PropEnum, Transfer

from ..core import Frame, TableModel
from .abstract import AbstractPlugin

__all__ = [
    'FramePropsPlugin'
]


def _create_enum_props_lut(enum: type[PropEnum], pretty_name: str) -> tuple[str, dict[str, dict[int, str]]]:
    return enum.prop_key, {
        pretty_name: {
            idx: enum.from_param(idx).pretty_string if enum.is_valid(idx) else 'Invalid'
            for idx in range(min(enum.__members__.values()) - 1, max(enum.__members__.values()) + 1)
        }
    }


_frame_props_excluded_keys = {
    # vs internals
    '_AbsoluteTime', '_DurationNum', '_DurationDen', '_PictType', '_Alpha',
    # Handled separately
    '_SARNum', '_SARDen',
    # source filters
    '_FrameNumber',
    # vstools set_output
    'Name'
}


_frame_props_lut = {
    '_Combed': {
        'Is Combed': [
            'No',
            'Yes'
        ]
    },
    '_Field': {
        'Frame Field Type': [
            'Bottom Field',
            'Top Field'
        ]
    },
    '_SceneChangeNext': {
        'Scene Cut': [
            'Current Scene',
            'End of Scene'
        ]
    },
    '_SceneChangePrev': {
        'Scene Change': [
            'Current Scene',
            'Start of Scene'
        ]
    }
} | dict([
    _create_enum_props_lut(enum, name)
    for enum, name in list[tuple[type[PropEnum], str]]([
        (FieldBased, 'Field Type'),
        (Matrix, 'Matrix'),
        (Transfer, 'Transfer'),
        (Primaries, 'Primaries'),
        (ChromaLocation, 'Chroma Location'),
        (ColorRange, 'Color Range')
    ])
])


class FramePropsPlugin(AbstractPlugin, QTableView):
    _plugin_name = 'Frame Props'

    def setup_ui(self) -> None:
        self.verticalHeader().hide()

    def on_current_frame_changed(self, frame: Frame) -> None:
        self.update_frame_props(self.main.current_output.props)

    def update_frame_props(self, props: FrameProps) -> None:
        data = []

        for key in sorted(props.keys()):
            if key in _frame_props_excluded_keys:
                continue

            if key in _frame_props_lut:
                title = next(iter(_frame_props_lut[key].keys()))
                value_str = _frame_props_lut[key][title][props[key]]  # type: ignore
            else:
                title = key[1:] if key.startswith('_') else key
                value_str = str(props[key])

            if value_str is not None:
                data.append([title, value_str])

        if '_SARNum' in props and '_SARDen' in props:
            data.append(['Pixel aspect ratio', f"{props['_SARNum']}/{props['_SARDen']}"])

        self.setModel(TableModel(data, ['Name', 'Data'], False))
