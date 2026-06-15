import os
import cv2
import easyocr
from app.services.image_processor import extract_cells
from app.test_mock_generator import generate_mock_screenshot

# Recreate mock screenshot
generate_mock_screenshot("mock_screenshot.png")

img = cv2.imread("mock_screenshot.png")
cells = extract_cells(img)
print("Cells extracted:", len(cells))

# Create debug_cells directory if it doesn't exist
os.makedirs("debug_cells", exist_ok=True)

# Save cells and print OCR
reader = easyocr.Reader(['tr', 'en'], gpu=False)

cells_by_row = {}
for c in sorted(cells, key=lambda x: (x.row, x.col)):
    if c.image is not None:
        cv2.imwrite(f"debug_cells/cell_r{c.row}_c{c.col}.png", c.image)
    cells_by_row.setdefault(c.row, []).append(c)

for row in sorted(cells_by_row.keys()):
    row_cells = sorted(cells_by_row[row], key=lambda c: c.col)
    row_texts = []
    for c in row_cells:
        # Check if column is school no (Col 1)
        if c.col == 1 and row >= 2:
            res = reader.readtext(c.image, allowlist="0123456789")
        elif row >= 2 and c.col in (3, 4, 5, 6):
            res = reader.readtext(c.image, allowlist="0123456789,.-Gg ")
        else:
            res = reader.readtext(c.image)
            
        txt = " ".join([r[1] for r in res]).strip()
        row_texts.append(f"C{c.col}: '{txt}'")
    print(f"Row {row}:", " | ".join(row_texts))
