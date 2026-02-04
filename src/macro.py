import time
import threading
from pynput.keyboard import Controller as KeyController
from pynput.mouse import Controller as MouseController, Button

key_ctrl = KeyController()
mouse = MouseController()

CONDITION_COMMANDS = ["holding", "single", "toggle"]

ACTION_COMMANDS = [
    "delay",
    "keydown", "keyup", "keytap",
    "repeat", "repeatend",
    "leftclickdown", "leftclickup", "leftclick",
    "rightclickdown", "rightclickup", "rightclick",
    "middleclickdown", "middleclickup", "middleclick",
    "scrollup", "scrolldown"
]


# parsed ctrl
class ParsedMacro:
    def __init__(self, mode, actions):
        self.mode = mode
        self.actions = actions


# parser
class ScriptParser:
    def parse(self, script_text: str) -> ParsedMacro:
        lines = [l.strip().lower() for l in script_text.splitlines() if l.strip()]
        if not lines:
            raise ValueError("Empty macro script")

        mode = lines[0]
        if mode not in CONDITION_COMMANDS:
            raise ValueError("First line must be a condition command")

        actions = []
        i = 1

        while i < len(lines):
            parts = lines[i].split()
            cmd = parts[0]

            if cmd not in ACTION_COMMANDS:
                raise ValueError(f"Unknown command: {cmd}")

            if cmd == "delay":
                actions.append(("delay", int(parts[1])))

            elif cmd in ["keydown", "keyup", "keytap"]:
                actions.append((cmd, parts[1]))

            elif cmd in [
                "leftclickdown", "leftclickup", "leftclick",
                "rightclickdown", "rightclickup", "rightclick",
                "middleclickdown", "middleclickup", "middleclick",
                "scrollup", "scrolldown"
            ]:
                actions.append((cmd,))

            elif cmd == "repeat":
                count = int(parts[1])
                loop_actions = []
                i += 1
                while lines[i] != "repeatend":
                    sub_parts = lines[i].split()
                    sub_cmd = sub_parts[0]

                    if sub_cmd == "delay":
                        loop_actions.append(("delay", int(sub_parts[1])))
                    elif sub_cmd in ["keydown", "keyup", "keytap"]:
                        loop_actions.append((sub_cmd, sub_parts[1]))
                    else:
                        loop_actions.append((sub_cmd,))
                    i += 1

                actions.append(("repeat", count, loop_actions))

            i += 1

        return ParsedMacro(mode, actions)


# executor
class ActionExecutor:
    def execute(self, action):
        cmd = action[0]

        if cmd == "delay":
            time.sleep(action[1] / 1000)

        elif cmd == "keydown":
            key_ctrl.press(action[1])

        elif cmd == "keyup":
            key_ctrl.release(action[1])

        elif cmd == "keytap":
            key_ctrl.press(action[1])
            time.sleep(0.1)
            key_ctrl.release(action[1])

        # LEFT MOUSE
        elif cmd == "leftclickdown":
            mouse.press(Button.left)
        elif cmd == "leftclickup":
            mouse.release(Button.left)
        elif cmd == "leftclick":
            mouse.click(Button.left)

        # RIGHT MOUSE
        elif cmd == "rightclickdown":
            mouse.press(Button.right)
        elif cmd == "rightclickup":
            mouse.release(Button.right)
        elif cmd == "rightclick":
            mouse.click(Button.right)

        # MIDDLE MOUSE
        elif cmd == "middleclickdown":
            mouse.press(Button.middle)
        elif cmd == "middleclickup":
            mouse.release(Button.middle)
        elif cmd == "middleclick":
            mouse.click(Button.middle)

        # SCROLL
        elif cmd == "scrollup":
            mouse.scroll(0, 1)
        elif cmd == "scrolldown":
            mouse.scroll(0, -1)

        # LOOP
        elif cmd == "repeat":
            count, loop_actions = action[1], action[2]
            for _ in range(count):
                for sub in loop_actions:
                    self.execute(sub)


# runtime
class MacroRuntime:
    def __init__(self):
        self.running = False
        self.executor = ActionExecutor()

    def _run(self, parsed):
        while self.running:
            for action in parsed.actions:
                if not self.running:
                    break
                self.executor.execute(action)

            if parsed.mode != "holding":
                break

        self.running = False

    def start(self, parsed):
        if parsed.mode == "single":
            self.running = True
            threading.Thread(target=self._run, args=(parsed,), daemon=True).start()

        elif parsed.mode == "toggle":
            self.running = not self.running
            if self.running:
                threading.Thread(target=self._run, args=(parsed,), daemon=True).start()

        elif parsed.mode == "holding":
            self.running = True
            threading.Thread(target=self._run, args=(parsed,), daemon=True).start()

    def stop(self):
        self.running = False
