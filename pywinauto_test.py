from pywinauto.application import Application, WindowSpecification
from time import sleep
import re

def save_file(window : WindowSpecification, file_name : str = "", file_path : str = "", override_existent : bool = False) -> None:
    save_as_dialog_popup = window.child_window(title="Save As", control_type="Window")
    
    if file_name:
        edit_field = save_as_dialog_popup.descendants(title="File name:", control_type="Edit")[0]
        edit_field.type_keys(file_name)
    if file_path:
        progress_bar = save_as_dialog_popup.descendants(title="Loading", control_type="ProgressBar")[0]
        toolbar_elem = progress_bar.descendants(control_type="ToolBar")[0]
        # print(dir(toolbar_elem))
        # toolbar_elem.set_focus()
        toolbar_elem.type_keys("{F4}")
        edit_elem = progress_bar.descendants(title="Address", control_type="Edit")[0]
        edit_elem.set_text(file_path)
        edit_elem.type_keys("{ENTER}")
    save_btn = save_as_dialog_popup.child_window(title="Save", control_type="Button")
    save_btn.click()

    try:
        confirm_save_popup = save_as_dialog_popup.child_window(title="Confirm Save As")
        button = confirm_save_popup.child_window(title=("Yes" if override_existent else "No"), control_type="Button")
        button.click()
    except:
        print("Unable to locate button or popup")
    return

def select_menu_item(item_name : str, window : WindowSpecification) -> None:
    application_menu = window.child_window(title="Application", control_type="MenuBar")
    menu_item = application_menu.child_window(title=item_name, control_type="MenuItem")

    menu_item.click_input()

    return

def open_new_file(window : WindowSpecification) -> None:
    
    select_menu_item(item_name="File", window=window)
    menu_popup = window.child_window(control_type="Menu", found_index=0)
    new_button = menu_popup.child_window(title='New\tCtrl+N', control_type="MenuItem")
    new_button.click_input()

def write_to_new_file(window : WindowSpecification) -> None:
    
    open_new_file(window=window)
    # print(f"Function WINDOW: {window.window_text()}")
    text_area = window.child_window(class_name="Scintilla")
    text_area.type_keys("OPENING new window to test functionality^s", with_spaces=True)
    
    save_file(window=window, file_name="test_pywinauto", file_path=r"C:\Users\Marko\Desktop\NEYHO", override_existent=True)

    return

def main():
    ###
    ### elem.print_control_identifiers()
    ###
    app = Application(backend="uia").start(r"C:\Program Files\Notepad++\notepad++.exe")
    top_window = app.top_window()

    textarea = top_window.child_window(class_name="Scintilla")

    textarea.type_keys("{ENTER}PyWinAuto")

    # print(f"MAIN WINDOW: {top_window.window_text()}")
    write_to_new_file(window=top_window)
  
    top_window.close()
    # exit()
    # w = pywinauto.findwindows.find_window(title="Untitled - Notepad", found_index=0)
    # print(w)
    # app = Application(backend="uia").connect(handle=w)

    # top_window = app.top_window()
    # top_window.set_focus()
    # top_window.print_control_identifiers()

    # top_window.child_window(control_type="Document").type_keys("MARKO")

    return

if __name__ == '__main__':
    main()