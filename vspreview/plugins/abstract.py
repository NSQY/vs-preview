from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generic, Iterable, NamedTuple, cast, overload

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QSizePolicy, QWidget
from jetpytools import SPath, T

from ..core import ExtendedWidgetBase, Frame, NotchProvider, QYAMLObject
from ..core.bases import yaml_Loader

import vapoursynth as vs

if TYPE_CHECKING:
    from ..main import MainWindow


__all__ = [
    'AbstractPlugin', 'PluginConfig', 'PluginSettings', 'PluginShortcut', 'SettingsNamespace',
    'WorkspacePlugin', 'WorkspaceConfig',

    'FileResolverPlugin', 'FileResolvePluginConfig', 'ResolvedScript'
]


class SettingsNamespace(dict[str, Any]):
    def __getattr__(self, __key: str) -> Any:
        return self.__getitem__(__key)

    def __setattr__(self, __key: str, __value: Any) -> None:
        return self.__setitem__(__key, __value)

    def __delattr__(self, __key: str) -> None:
        return self.__delitem__(__key)

    def __setstate__(self, state: dict[str, dict[str, Any]]) -> None:
        self.update(state)

yaml_Loader.add_constructor(f'tag:yaml.org,2002:python/object:{SettingsNamespace.__module__}.{SettingsNamespace.__name__}', lambda _self, node: SettingsNamespace())
yaml_Loader.add_constructor(f'tag:yaml.org,2002:python/object/new:{SettingsNamespace.__module__}.{SettingsNamespace.__name__}', lambda self, node: SettingsNamespace(self.construct_mapping(node)["dictitems"]))


class PluginSettings(QYAMLObject):
    def __init__(self, plugin: AbstractPlugin) -> None:
        self.plugin = plugin
        self.local = SettingsNamespace()
        self.globals = SettingsNamespace()
        self.fired_events = [False, False]

    def __getstate__(self) -> dict[str, dict[str, Any]]:
        return {'local': self.local, 'globals': self.globals}

    def __setstate__(self, isglobal: bool) -> None:
        self.fired_events[int(isglobal)] = True
        if all(self.fired_events):
            self.fired_events = [False, False]
            self.plugin.__setstate__()


if TYPE_CHECKING:
    class _BasePluginConfig(NamedTuple):
        namespace: str
        display_name: str
        settings_type: type[PluginSettings] = PluginSettings

    class _BasePlugin:
        _config: ClassVar[_BasePluginConfig]
        settings: PluginSettings
else:
    _BasePlugin, _BasePluginConfig = object, Generic[T]


class PluginConfig(_BasePluginConfig, NamedTuple):  # type: ignore
    namespace: str
    display_name: str
    visible_in_tab: bool = True
    settings_type: type[PluginSettings] = PluginSettings
    workspace: bool = False


class WorkspaceConfig(PluginConfig):
    def __new__(cls, namespace: str, display_name: str, visible_in_tab: bool = False, settings_type: type[PluginSettings] = PluginSettings) -> WorkspaceConfig:
        return super().__new__(cls, namespace, display_name, visible_in_tab, settings_type, True)


class FileResolvePluginConfig(_BasePluginConfig, NamedTuple):  # type: ignore
    namespace: str
    display_name: str
    settings_type: type[PluginSettings] = PluginSettings


class ResolvedScript(NamedTuple):
    path: Path
    display_name: str
    arguments: dict[str, Any] = {}
    reload_enabled: bool = True


class PluginShortcut(NamedTuple):
    name: str
    parent: QObject | str
    handler: Callable[[], None] | str
    key: QKeySequence | None = None
    description: str | None = None


class AbstractPlugin(ExtendedWidgetBase, NotchProvider):
    _config: ClassVar[PluginConfig]
    settings: PluginSettings
    shortcuts: list[PluginShortcut]

    on_first_load = pyqtSignal()

    index: int = -1

    def __init__(self, main: MainWindow) -> None:
        try:
            super().__init__(main)  # type: ignore
            self.init_notches(main)

            assert isinstance(self, QWidget)
        except TypeError as e:
            print('\tMake sure you\'re inheriting a QWidget!\n')

            raise e

        self.main = main

        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        self._first_load_done = False

        self.shortcuts = []
        self.__legacy_counter_shortcuts = 0
        self.add_shortcuts()

    def first_load(self) -> bool:
        if not self._first_load_done:
            self.setup_ui()

            self.setup_shortcuts()

            self.set_qobject_names()

            self.on_first_load.emit()  # type: ignore

            self._first_load_done = True

            return True

        return False

    def init_outputs(self) -> None:
        ...

    def setup_shortcuts(self) -> None:
        self.main.shortcuts.sections_plugins[self._config.namespace].setup_shortcuts()

    @overload
    def add_shortcut(
        self,
        name: str,
        parent: QObject | str,
        /,
        handler: Callable[[], None] | str,
        key: QKeySequence | None = None,
        description: str | None = None
    ) -> None:
        ...

    @overload
    def add_shortcut(
        self,
        key: Qt.Key | int,
        handler: Callable[[], None],
        /
    ) -> None:
        """Legacy"""
        ...

    def add_shortcut(
        self,
        name_or_key: Any,
        parent_or_handler: Any,
        /,
        handler: Callable[[], None] | str = "",
        key: QKeySequence | None = None,
        description: str | None = None
    ) -> None:
        if isinstance(name_or_key, str) and isinstance(parent_or_handler, (QObject | str)):
            name, parent, handler = name_or_key, parent_or_handler, handler
        else:
            name, parent, = f"shortcut_{self.__legacy_counter_shortcuts}", cast(QObject, self), 
            handler, key = parent_or_handler, QKeySequence(name_or_key)
            description = f"Shortcut {self.__legacy_counter_shortcuts}"
            self.__legacy_counter_shortcuts += 1

        self.shortcuts.append(PluginShortcut(name, parent, handler, key, description))

    def add_shortcuts(self) -> None:
        ...

    def on_current_frame_changed(self, frame: Frame) -> None:
        ...

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        ...

    @property
    def is_notches_visible(self) -> bool:
        return (
            not self._config.visible_in_tab
        ) or self.index == self.main.plugins.plugins_tab.currentIndex()  # type: ignore

    def __setstate__(self) -> None:
        ...


class WorkspacePlugin(AbstractPlugin, QWidget):
    """Plugin that creates a custom viewport/workspace instead of a sidebar widget."""

    _config: ClassVar[PluginConfig]

    def __init__(self, main: MainWindow) -> None:
        super().__init__(main)
        self._is_active = False

    def activate_workspace(self) -> None:
        """Called when this workspace becomes the active viewport."""
        self._is_active = True
        self.on_workspace_activated()

    def deactivate_workspace(self) -> None:
        """Called when this workspace is no longer the active viewport."""
        self._is_active = False
        self.on_workspace_deactivated()

    def on_workspace_activated(self) -> None:
        """Override this method to handle workspace activation."""
        pass

    def on_workspace_deactivated(self) -> None:
        """Override this method to handle workspace deactivation."""
        pass

    @property
    def is_active(self) -> bool:
        """Returns True if this workspace is currently active."""
        return self._is_active

    def get_workspace_node(self, original_node: vs.VideoNode) -> vs.VideoNode:
        """
        Override this method to return a modified version of the node for the workspace.

        Args:
            original_node: The original video node from the script

        Returns:
            The modified video node for this workspace
        """
        return original_node

    def get_workspace_display_name(self) -> str:
        """Returns the PluginConfig.display_name for this workspace."""
        return self._config.display_name

    def setup_ui(self) -> None:
        """
        Setup UI for workspace plugin.
        This function is called when the workspace is activated.
        """
        pass


class FileResolverPlugin:
    _config: ClassVar[FileResolvePluginConfig]
    settings: PluginSettings

    temp_handles = set[SPath]()

    def get_extensions(self) -> Iterable[str]:
        return []

    def can_run_file(self, filepath: Path) -> bool:
        raise NotImplementedError

    def resolve_path(self, filepath: Path) -> ResolvedScript:
        raise NotImplementedError

    def cleanup(self) -> None:
        for file in self.temp_handles:
            try:
                if not file.exists():
                    continue

                if file.is_dir():
                    file.rmdirs(True)
                else:
                    file.unlink(True)
            except PermissionError:
                continue

    def get_temp_path(self, is_folder: bool = False) -> SPath:
        from tempfile import mkdtemp, mkstemp

        if is_folder:
            temp = mkdtemp()
        else:
            temp = mkstemp()[1]

        temp_path = SPath(temp)

        self.temp_handles.add(temp_path)

        return temp_path


_BasePluginT = _BasePlugin | AbstractPlugin | FileResolverPlugin
