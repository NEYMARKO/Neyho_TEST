from pywinauto.application import Application, WindowSpecification
import pywinauto
from time import sleep
import re

def save_file(window : WindowSpecification, file_name : str = "", file_path : str = "") -> None:
    save_as_dialog_popup = window.child_window(title="Save As", control_type="Window")
    
    if file_name:
        edit_field = save_as_dialog_popup.descendants(title="File name:", control_type="Edit")[0]
        edit_field.type_keys(file_name)
    if file_path:
        progress_bar = save_as_dialog_popup.descendants(title="Loading", control_type="ProgressBar")[0]
        toolbar_elem = progress_bar.descendants(control_type="ToolBar")[0]
        print(dir(toolbar_elem))
        toolbar_elem.set_focus()
        toolbar_elem.type_keys("{F4}")
        edit_elem = progress_bar.descendants(title="Address", control_type="Edit")[0]
        edit_elem.set_text(file_path)
        edit_elem.type_keys("{ENTER}")

        # print(len(all_toolbar_elems))
        # for el in all_toolbar_elems:
            # print(f"ELEMENT: {el.window_text()}")
        # address_field = [tb for tb in all_toolbar_elems if re.search("Address", tb.window_text())][0]
        # address_field.type_keys(file_path)
        # sleep(5)
    save_btn = save_as_dialog_popup.child_window(title="Save", control_type="Button")
    sleep(5)
    save_btn.click()
    # save_as_dialog_popup.close()
    return

def open_new_tab(tab_name : str, window : WindowSpecification) -> None:
    application_menu = window.child_window(title="Application", control_type="MenuBar")
    menu_item = application_menu.child_window(title=tab_name, control_type="MenuItem")

    # sleep(0.25)
    menu_item.click_input()
    # Allow popup to appear
    # sleep(0.5)
    # menu_window = menu_item.child_window(title=tab_name, control_type="Window")
    menu_popup = window.child_window(control_type="Menu", found_index=0)
    new_button = menu_popup.child_window(title='New\tCtrl+N', control_type="MenuItem")
    new_button.click_input()
    # sleep(2)
    
    print(f"Function WINDOW: {window.window_text()}")
    text_area = window.child_window(class_name="Scintilla")
    text_area.type_keys("OPENING new window to test functionality^s")
    # save_as_dlg = window.child_window(title="Save As", control_type="Window")
    # save_btn = save_as_dlg.child_window(title="Save", control_type="Button")
    save_file(window=window, file_name="test_pywinauto", file_path=r"C:\Users\Marko\Desktop")
    # save_btn.click()
    # sleep(1)
    # window.type_keys("^s")
    return

def main():
    app = Application(backend="uia").start(r"C:\Program Files\Notepad++\notepad++.exe")
    top_window = app.top_window()

    # top_window.print_control_identifiers()
    # top_window.wait('exists ready visible enabled', timeout=5)
    textarea = top_window.child_window(class_name="Scintilla")

    textarea.type_keys("{ENTER}PyWinAuto")

    print(f"MAIN WINDOW: {top_window.window_text()}")
    open_new_tab(tab_name="File", window=top_window)
    # child_windows = top_window.children()
    # for child in child_windows:
    #     print(f"CHILDREN: {child.window_text()}")
    # print(f"TOP WINDOW: {top_window.window_text()}")
    # dlg = app.window(title_re=r".*Notepad\+\+")
    # dlg.wait("visible", timeout=20)
    # print("Found window:", dlg.window_text())
    # for w in app.windows():
    #     print(f"WINDOW: {w.window_text()}")
    # print("Main window:", dlg.window_text())
    # dlg.close()
    # sleep(2)
    top_window.close()
    exit()
    w = pywinauto.findwindows.find_window(title="Untitled - Notepad", found_index=0)
    print(w)
    app = Application(backend="uia").connect(handle=w)

    top_window = app.top_window()
    top_window.set_focus()
    top_window.print_control_identifiers()

    top_window.child_window(control_type="Document").type_keys("MARKO")

    exit()
    app = Application().start("notepad.exe")
    # app_window = app.top_window()
    # app_window.print_control_identifiers()
    # exit()
    notepad_window = app["Untitled"]
    notepad_window.wait("exists", timeout=5)
    print(notepad_window.exists())
    # notepad_window = n_w.wait('visible')
    notepad_window.type_keys("MARKO")
    notepad_window.child_window()
    notepad_window.print_control_identifiers()
    return

if __name__ == '__main__':
    main()