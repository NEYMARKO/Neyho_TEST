import time
from pywinauto import Desktop, WindowSpecification
from pywinauto.timings import wait_until
from pywinauto.controls.uiawrapper import UIAWrapper
import subprocess
import pyautogui

def select_line_item(name : str, ancestor_element : WindowSpecification | UIAWrapper) -> None:
    wait_until(
        timeout=10,
        retry_interval=0.5,
        func=lambda: len(ancestor_element.descendants(title=name, control_type="ListItem")) > 0
    )

    list_item = ancestor_element.descendants(title=name, control_type="ListItem")[0]
    list_item.click_input()

    return

def exit_app(ancestor_element : WindowSpecification | UIAWrapper) -> None:
    close_btn = ancestor_element.descendants(title="Close Calculator", control_type="Button")[0]
    close_btn.click_input()

    return

def main():
    subprocess.Popen(["explorer.exe", "calculator://"])

    calc_win = Desktop(backend="uia").window(title_re="Calculator")
    btn_candidates = calc_win.descendants(title="Maximize Calculator", control_type="Button")
    if btn_candidates:
        maximize_btn = calc_win.descendants(title="Maximize Calculator", control_type="Button")[0]
        maximize_btn.click_input()

    calc_win.set_focus()

    calc_body = calc_win.descendants(control_type="Custom")[0]
    navigation_btn = calc_body.children(title="Open Navigation", control_type="Button")[0]

    navigation_btn.click_input()

    select_line_item(name="Scientific Calculator", ancestor_element=calc_body)

    pyautogui.write(f"280 - 13", interval=0.1)
    pyautogui.press("enter")
    exit_app(ancestor_element=calc_win)

    # calc_win.print_control_identifiers()
    return

if __name__ == "__main__":
    main()