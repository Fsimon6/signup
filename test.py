import pyautogui, time
print("请将鼠标移动到飞书表格左上角定位框上，5秒后打印坐标...")
time.sleep(5)
x, y = pyautogui.position()
print(f"定位框坐标：({x}, {y})")