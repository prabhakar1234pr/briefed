from rembg import remove
from PIL import Image

SRC = r"C:\Users\prabh\.cursor\projects\c-briefed\assets\c__Users_prabh_AppData_Roaming_Cursor_User_workspaceStorage_c0beecbbfe0e9adf68f3cf02349bad74_images_remove_ai_and_give_me_202605292129-7ca4fffd-bda6-475e-8043-e2631587e153.png"
OUT = r"C:\briefed\frontend\public\assets\logo-b.png"

img = Image.open(SRC).convert("RGBA")
out = remove(img)

bbox = out.getbbox()
if bbox:
    out = out.crop(bbox)

out.save(OUT)
print("Saved", OUT, out.size)
