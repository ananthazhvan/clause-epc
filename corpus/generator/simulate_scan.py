import os
import fitz  # PyMuPDF
from PIL import Image
import io
import random

RENDERED_DIR = "corpus/rendered"

def simulate_scan_on_page(pdf_name, page_index):
    pdf_path = os.path.join(RENDERED_DIR, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
        
    print(f"Applying scan simulation to {pdf_name} page {page_index + 1}...")
    
    # 1. Open original PDF
    doc = fitz.open(pdf_path)
    if len(doc) <= page_index:
        print(f"Page index {page_index} out of range for {pdf_name}")
        return
        
    page = doc[page_index]
    
    # 2. Render page to high-res pixmap (150 DPI)
    pix = page.get_pixmap(dpi=150)
    img_data = pix.tobytes("png")
    
    # 3. Load into Pillow
    img = Image.open(io.BytesIO(img_data)).convert("RGB")
    
    # 4. Rotate slightly (between 0.3 and 0.7 degrees, randomly positive or negative)
    angle = random.uniform(0.3, 0.7) * random.choice([1, -1])
    rotated = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
    
    # 5. Apply light salt & pepper scan noise (0.015% dark speckles)
    width, height = rotated.size
    pixels = rotated.load()
    num_noise_pixels = int(width * height * 0.00015)
    for _ in range(num_noise_pixels):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        # Random grey speckles
        grey = random.randint(80, 160)
        pixels[x, y] = (grey, grey, grey)
        
    # 6. Save image to PDF bytes in memory
    pdf_bytes_io = io.BytesIO()
    rotated.save(pdf_bytes_io, format="PDF")
    pdf_bytes_io.seek(0)
    
    # 7. Insert the new image page back into the PDF using PyMuPDF
    img_doc = fitz.open("pdf", pdf_bytes_io.read())
    
    # Create a new document to hold the merged result safely
    new_doc = fitz.open()
    for i in range(len(doc)):
        if i == page_index:
            new_doc.insert_pdf(img_doc, from_page=0, to_page=0)
        else:
            new_doc.insert_pdf(doc, from_page=i, to_page=i)
            
    # Save the modified document over the original
    new_doc.save(pdf_path, garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    img_doc.close()
    print(f"Successfully simulated scan on {pdf_name} page {page_index + 1}.")

def main():
    # Simulate scan on the 3 main submittals' page 2 (index 1) - the product datasheets
    targets = [
        ("submittal_Deccan_generator.pdf", 1),
        ("submittal_VoltEdge_UPS_R1.pdf", 1),
        ("submittal_CryoCore_CRAH.pdf", 1)
    ]
    
    for pdf_name, page_idx in targets:
        simulate_scan_on_page(pdf_name, page_idx)
        
    print("Scan simulation pass complete!")

if __name__ == "__main__":
    main()
