from imgui_bundle import imgui, hello_imgui
from pynput import keyboard
import threading, json, os
from macro import ScriptParser, MacroRuntime

DATA_FILE = "macros.json"
WINDOW_W = 1200
WINDOW_H = 650

parser = ScriptParser()
runtime = MacroRuntime()

# json
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "selected_config": "config 1",
            "configs": {"config 1": {"macros": {}}}
        }
        save_data(data)
        return data
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data_lock = threading.Lock()
data = load_data()

selected_macro_index = -1
macro_name = ""
macro_script = ""
keybind = "None"
waiting_for_keybind = False
rename_buffer = ""


# macro
def load_macro_by_index(index):
    global macro_name, macro_script, keybind
    cfg = data["selected_config"]
    macros = list(data["configs"][cfg]["macros"].items())
    if 0 <= index < len(macros):
        name, macro = macros[index]
        macro_name = name
        macro_script = macro["script"]
        keybind = macro["keybind"]


# listener
def on_press(key):
    global waiting_for_keybind, keybind
    try:
        pressed = key.char
    except AttributeError:
        pressed = str(key)

    # Capture new keybind
    if waiting_for_keybind:
        keybind = pressed
        waiting_for_keybind = False
        print(f"Bound to: {keybind}")
        return

    # Run macro
    with data_lock:
        cfg = data["selected_config"]
        for name, macro in data["configs"][cfg]["macros"].items():
            if macro["enabled"] and macro["keybind"] == pressed:
                try:
                    parsed = parser.parse(macro["script"])
                    runtime.start(parsed)
                except Exception as e:
                    print("Macro error:", e)


def on_release(key):
    # Needed for holding mode
    runtime.stop()


threading.Thread(
    target=lambda: keyboard.Listener(on_press=on_press, on_release=on_release).start(),
    daemon=True
).start()


# ui
def gui():
    global selected_macro_index, macro_name, macro_script, keybind, waiting_for_keybind, rename_buffer

    imgui.set_next_window_pos((0, 0), imgui.Cond_.always)
    imgui.set_next_window_size((WINDOW_W, WINDOW_H), imgui.Cond_.always)
    imgui.begin("MainUI", None, imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.no_resize | imgui.WindowFlags_.no_move)

    imgui.dummy((0, 12))

    # lp
    imgui.begin_child("left", (360, 0), True)

    configs = list(data["configs"].keys())
    current_cfg = data["selected_config"]
    current_index = configs.index(current_cfg)

    changed, new_index = imgui.combo("Config", current_index, configs)
    if changed:
        data["selected_config"] = configs[new_index]
        save_data(data)
        selected_macro_index = -1

    imgui.same_line()

    if imgui.small_button("+"):
        base = "config"
        i = 1
        while f"{base} {i}" in data["configs"]:
            i += 1
        new_name = f"{base} {i}"
        data["configs"][new_name] = {"macros": {}}
        data["selected_config"] = new_name
        save_data(data)

    imgui.same_line()

    if imgui.small_button("✎"):
        rename_buffer = current_cfg
        imgui.open_popup("rename_config_popup")

    imgui.same_line()

    if imgui.small_button("X") and len(data["configs"]) > 1:
        del data["configs"][current_cfg]
        data["selected_config"] = list(data["configs"].keys())[0]
        save_data(data)
        selected_macro_index = -1

    if imgui.begin_popup("rename_config_popup"):
        changed, rename_buffer = imgui.input_text("New Name", rename_buffer, 64)

        if imgui.button("Apply"):
            new_name = rename_buffer.strip()
            if new_name and new_name not in data["configs"]:
                data["configs"][new_name] = data["configs"].pop(current_cfg)
                data["selected_config"] = new_name
                save_data(data)
            imgui.close_current_popup()

        imgui.same_line()
        if imgui.button("Cancel"):
            imgui.close_current_popup()

        imgui.end_popup()

    imgui.separator()

    cfg = data["selected_config"]
    macros_dict = data["configs"][cfg]["macros"]
    macro_items = list(macros_dict.items())

    for i, (name, macro) in enumerate(macro_items):
        changed, macro["enabled"] = imgui.checkbox(f"##enable_{i}", macro["enabled"])
        if changed:
            save_data(data)

        imgui.same_line()
        if imgui.button(name, (-1, 0)):
            selected_macro_index = i
            load_macro_by_index(i)

    if imgui.button("New Macro"):
        macros_dict[f"macro {len(macro_items)+1}"] = {"enabled": True, "script": "", "keybind": "None"}
        save_data(data)

    imgui.end_child()
    imgui.same_line()

    # script
    imgui.begin_child("middle", (520, 0), True)
    imgui.text("Script")
    _, macro_script = imgui.input_text_multiline("##script", macro_script, (500, 420))
    imgui.end_child()
    imgui.same_line()

    # right
    imgui.begin_child("right", (0, 0), True)

    imgui.text("Name")
    _, macro_name = imgui.input_text("##name", macro_name)

    imgui.spacing()
    imgui.text("Keybind")

    if waiting_for_keybind:
        imgui.button("Press key...", (200, 40))
    else:
        if imgui.button(keybind, (200, 40)):
            waiting_for_keybind = True

    imgui.spacing()

    if imgui.button("Save", (140, 45)) and selected_macro_index != -1:
        old_name = list(macros_dict.keys())[selected_macro_index]
        macros_dict[macro_name] = {
            "enabled": macros_dict[old_name]["enabled"],
            "script": macro_script,
            "keybind": keybind
        }
        if macro_name != old_name:
            del macros_dict[old_name]
        save_data(data)

    imgui.end_child()
    imgui.end()


# run
params = hello_imgui.RunnerParams()
params.app_window_params.window_title = "MacroLite"
params.app_window_params.window_geometry.size = (WINDOW_W, WINDOW_H)
params.app_window_params.borderless = True
params.app_window_params.resizable = False
params.callbacks.show_gui = gui

hello_imgui.run(params)
