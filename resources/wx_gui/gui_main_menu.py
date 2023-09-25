# Generate GUI for main menu
import wx
import sys
import logging
import threading
import webbrowser
import subprocess

from pathlib import Path

from resources.wx_gui import (
    gui_build,
    gui_macos_installer_download,
    gui_support,
    gui_help,
    gui_settings,
    gui_sys_patch_display,
    gui_update,
)
from resources import (
    constants,
    global_settings,
    updates
)
from data import os_data


class MainFrame(wx.Frame):
    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None):
        logging.info("Initializing Main Menu Frame")
        super(MainFrame, self).__init__(parent, title=title, size=(600, 400), style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        gui_support.GenerateMenubar(self, global_constants).generate()

        self.constants: constants.Constants = global_constants
        self.title: str = title

        self.model_label: wx.StaticText = None
        self.build_button: wx.Button = None

        self.constants.update_stage = gui_support.AutoUpdateStages.INACTIVE

        self._generate_elements()

        self.Centre()
        self.Show()


        self._preflight_checks()


    def _generate_elements(self) -> None:
        """
        Generate UI elements for the main menu

        Format:
          - Title label: OpenCore Legacy Patcher v{X.Y.Z}
          - Text:        Model: {Build or Host Model}
          - Buttons:
            - Build and Install OpenCore
            - Post-Install Root Patch
            - Create macOS Installer
            - Settings
            - Help
          - Text:        Copyright
        """

        # Title label: OpenCore Legacy Patcher v{X.Y.Z}
        title_label = wx.StaticText(self, label=f"OpenCore Legacy Patcher {'' if self.constants.special_build else 'v'}{self.constants.patcher_version}", pos=(-1, 10))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        # Text: Model: {Build or Host Model}
        model_label = wx.StaticText(self, label=f"Model: {self.constants.custom_model or self.constants.computer.real_model}", pos=(-1, title_label.GetPosition()[1] + 25
                                                                                                                                    ))
        model_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        model_label.Centre(wx.HORIZONTAL)
        self.model_label = model_label

        # Buttons:
        menu_buttons = {
            "Build and Install OpenCore": {
                "function": self.on_build_and_install,
                "description": [
                    "Prepares provided drive to be able",
                    "to boot unsupported OSes.",
                    "Use on installers or internal drives."
                ],
                "icon": str(self.constants.icns_resource_path / "OC-Build.icns"),
            },
            "Create macOS Installer": {
                "function": self.on_create_macos_installer,
                "description": [
                    "Download and flash a macOS",
                    "Installer for your system.",
                ],
                "icon": str(self.constants.icns_resource_path / "OC-Installer.icns"),
            },
            "⚙️ Settings": {
                "function": self.on_settings,
                "description": [
                ],
            },
            "Post-Install Root Patch": {
                "function": self.on_post_install_root_patch,
                "description": [
                    "Installs hardware drivers and",
                    "patches for your system after",
                    "installing a new version of macOS.",
                ],
                "icon": str(self.constants.icns_resource_path / "OC-Patch.icns"),
            },

            "Support": {
                "function": self.on_help,
                "description": [
                    "Resources for OpenCore Legacy",
                    "Patcher.",
                ],
                "icon": str(self.constants.icns_resource_path / "OC-Support.icns"),
            },
        }
        button_x = 30
        button_y = model_label.GetPosition()[1] + 30
        rollover = len(menu_buttons) / 2
        if rollover % 1 != 0:
            rollover = int(rollover) + 1
        max_height = 0
        for index, (button_name, button_function) in enumerate(menu_buttons.items(), start=1):
            # place icon
            if "icon" in button_function:
                icon = wx.StaticBitmap(self, bitmap=wx.Bitmap(button_function["icon"], wx.BITMAP_TYPE_ICON), pos=(button_x - 10, button_y), size=(64, 64))
                if button_name == "Build and Install OpenCore":
                    icon.SetSize((70, 70))
                elif button_name == "Create macOS Installer":
                    icon.SetPosition((button_x - 5, button_y + 3))
                elif button_name == "Post-Install Root Patch":
                    icon.SetPosition((-1, button_y + 7))
                elif button_name == "Support":
                    # icon_mac.SetSize((80, 80))
                    icon.SetPosition((button_x - 7, button_y + 3))
            if button_name == "⚙️ Settings":
                button_y += 5

            button = wx.Button(self, label=button_name, pos=(button_x + 70, button_y), size=(180, 30))
            button.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
            button.Bind(wx.EVT_BUTTON, lambda event, function=button_function["function"]: function(event))
            button_y += 30

            # # Text: Description
            description_label = wx.StaticText(self, label='\n'.join(button_function["description"]), pos=(button_x + 75, button.GetPosition()[1] + button.GetSize()[1] + 3))
            description_label.SetFont(gui_support.font_factory(10, wx.FONTWEIGHT_NORMAL))
            # button_y += 15

            for i, line in enumerate(button_function["description"]):
                if line == "":
                    continue
                button_y += 11 if i == 0 else 13
            button_y += 25

            if button_name == "Build and Install OpenCore":
                self.build_button = button
                if gui_support.CheckProperties(self.constants).host_can_build() is False:
                    button.Disable()
            elif button_name == "Post-Install Root Patch":
                if self.constants.detected_os < os_data.os_data.big_sur:
                    button.Disable()
            elif button_name == "⚙️ Settings":
                button.SetSize((100, -1))
                button.Centre(wx.HORIZONTAL)
                description_label.Centre(wx.HORIZONTAL)

            if index == rollover:
                max_height = button_y
                button_x = 320
                button_y = model_label.GetPosition()[1] + 30


        # Text: Copyright
        copy_label = wx.StaticText(self, label=self.constants.copyright_date, pos=(-1, max_height - 15))
        copy_label.SetFont(gui_support.font_factory(10, wx.FONTWEIGHT_NORMAL))
        copy_label.Centre(wx.HORIZONTAL)

        # Set window size
        self.SetSize((-1, copy_label.GetPosition()[1] + 50))


    def _preflight_checks(self):
        if (
                self.constants.computer.build_model != None and
                self.constants.computer.build_model != self.constants.computer.real_model and
                self.constants.host_is_hackintosh is False
            ):
            # Notify user they're booting an unsupported configuration
            pop_up = wx.MessageDialog(
                self,
                f"We found you are currently booting OpenCore built for a different unit: {self.constants.computer.build_model}\n\nWe builds configs to match individual units and cannot be mixed or reused with different Macs.\n\nPlease Build and Install a new OpenCore config, and reboot your Mac.",
                "Unsupported Configuration Detected!",
                style=wx.OK | wx.ICON_EXCLAMATION
            )
            pop_up.ShowModal()
            self.on_build_and_install()
            return

        self._fix_local_install()

        if "--update_installed" in sys.argv and self.constants.has_checked_updates is False and gui_support.CheckProperties(self.constants).host_can_build():
            # Notify user that the update has been installed
            self.constants.has_checked_updates = True
            pop_up = wx.MessageDialog(
                self,
                f"OpenCore Legacy Patcher has been updated to the latest version: {self.constants.patcher_version}\n\nWould you like to update OpenCore and your root volume patches?",
                "Update successful!",
                style=wx.YES_NO | wx.YES_DEFAULT | wx.ICON_INFORMATION
            )
            pop_up.ShowModal()

            if pop_up.GetReturnCode() != wx.ID_YES:
                logging.info("Skipping OpenCore and root volume patch update...")
                return


            logging.info("Updating OpenCore and root volume patches...")
            self.constants.update_stage = gui_support.AutoUpdateStages.CHECKING
            self.Hide()
            pos = self.GetPosition()
            gui_build.BuildFrame(
                parent=None,
                title=self.title,
                global_constants=self.constants,
                screen_location=pos
            )
            self.Close()

        threading.Thread(target=self._check_for_updates).start()


    def _fix_local_install(self) -> None:
        """
        Work-around users manually copying the app to /Applications
        We'll delete the app, and create a proper symlink
        Note: This *shouldn't* be needed with installs after 0.6.7, but it's a good catch-all
        """

        if "--update_installed" not in sys.argv:
            return
        if self.constants.has_checked_updates is True:
            return

        # Check if app exists in /Applications, and is not a symlink
        if Path("/Applications/OpenCore-Patcher.app").exists() and Path("/Applications/OpenCore-Patcher.app").is_symlink() is False:
            logging.info("Found user-installed app in /Applications, replacing with symlink")
            # Delete app
            result = subprocess.run(["rm", "-rf", "/Applications/OpenCore-Patcher.app"], capture_output=True)
            if result.returncode != 0:
                logging.info("Failed to delete app from /Applications")
                return

            # Create symlink
            result = subprocess.run(["ln", "-s", "/Library/Application Support/Dortania/OpenCore-Patcher.app", "/Applications/OpenCore-Patcher.app"], capture_output=True)
            if result.returncode != 0:
                logging.info("Failed to create symlink to /Applications")
                return


    def _check_for_updates(self):
        if self.constants.has_checked_updates is True:
            return

        ignore_updates = global_settings.GlobalEnviromentSettings().read_property("IgnoreAppUpdates")
        if ignore_updates is True:
            self.constants.ignore_updates = True
            return

        self.constants.ignore_updates = False
        self.constants.has_checked_updates = True
        dict = updates.CheckBinaryUpdates(self.constants).check_binary_updates()
        if not dict:
            return

        version = dict["Version"]
        logging.info(f"New version: {version}")
        dialog = wx.MessageDialog(
            parent=self,
            message=f"Current Version: {self.constants.patcher_version}{' (Nightly)' if not self.constants.commit_info[0].startswith('refs/tags') else ''}\nNew version: {version}\nWould you like to update?",
            caption="Update Available for OpenCore Legacy Patcher!",
            style=wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
        )
        dialog.SetYesNoCancelLabels("Download and install", "Ignore", "View on Github")
        response = dialog.ShowModal()

        if response == wx.ID_YES:
            wx.CallAfter(self.on_update, dict["Link"], version)
        elif response == wx.ID_CANCEL:
            webbrowser.open(dict["Github Link"])


    def on_build_and_install(self, event: wx.Event = None):
        self.Hide()
        gui_build.BuildFrame(
            parent=None,
            title=self.title,
            global_constants=self.constants,
            screen_location=self.GetPosition()
        )
        self.Destroy()


    def on_post_install_root_patch(self, event: wx.Event = None):
        gui_sys_patch_display.SysPatchDisplayFrame(
            parent=self,
            title=self.title,
            global_constants=self.constants,
            screen_location=self.GetPosition()
        )


    def on_create_macos_installer(self, event: wx.Event = None):
        gui_macos_installer_download.macOSInstallerDownloadFrame(
            parent=self,
            title=self.title,
            global_constants=self.constants,
            screen_location=self.GetPosition()
        )


    def on_settings(self, event: wx.Event = None):
        gui_settings.SettingsFrame(
            parent=self,
            title=self.title,
            global_constants=self.constants,
            screen_location=self.GetPosition()
        )

    def on_help(self, event: wx.Event = None):
        gui_help.HelpFrame(
            parent=self,
            title=self.title,
            global_constants=self.constants,
            screen_location=self.GetPosition()
        )

    def on_update(self, oclp_url: str, oclp_version: str):
        gui_update.UpdateFrame(
            parent=self,
            title=self.title,
            global_constants=self.constants,
            screen_location=self.GetPosition(),
            url=oclp_url,
            version_label=oclp_version
        )