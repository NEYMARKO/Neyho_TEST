import os
import cv2
import pymupdf
from pathlib import Path
import pytesseract

tesseract_path = r"C:\Program Files\Tesseract-OCR"
os.environ['TESSDATA_PREFIX'] = os.path.join(tesseract_path, 'tessdata')
pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_path, 'tesseract.exe')

def main():
    root_folder_path_obj = Path(__file__).parent
    image_output_folder_path_obj = root_folder_path_obj / "imgs"
    if not image_output_folder_path_obj.exists():
        image_output_folder_path_obj.mkdir(parents=True, exist_ok=True)
    
    print(f"Working directory: {root_folder_path_obj}")
    
    pdf_path = root_folder_path_obj / "ocr.pdf"
    doc = pymupdf.open(pdf_path)
    
    image_list = doc[0].get_images()
    if image_list:
        print(f"Found {len(image_list)} images on page 0")
    else:
        print("No images found on page 0")

    page = doc[0]
    res = 72
    mat = pymupdf.Matrix(4, 4)
    pix = page.get_pixmap(matrix=mat)
    if pix.alpha:
        pix.set_alpha(None)

    # pix.invert_irect(pymupdf.IRect(x0=0, y0=0, x1=pix.width, y1=pix.height))
    gamma = 0.85
    # pix.gamma_with(gamma)
    # pix.gamma_with(gamma)
    img_path = f"{image_output_folder_path_obj.absolute()}/res_{res}-gamma_{gamma}.png"
    pix.save(str(img_path))
    
    # image = cv2.imread(str(img_path))
    # gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # # blur = cv2.GaussianBlur(gray, (3, 3), 0)
    # blur = cv2.blur(gray, (2,2))
    # # thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    # opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    # # opening = cv2.dilate(thresh, kernel, iterations=1)
    # # opening = cv2.erode(thresh, opening, iterations=1)
    # invert = 255 - opening

    # data = pytesseract.image_to_string(invert, lang='mkd', config='--psm 6')
    # print(data)
    # # cv2.imshow('opening', opening)
    # # cv2.imshow('blur', blur)
    # cv2.imshow('blur', blur)
    # cv2.imshow('invert', invert)
    # cv2.waitKey()
    # Read image
    image = cv2.imread(str(img_path))

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Option 1: Simple approach (often best for clean documents)
    # Just use adaptive threshold, no morphology
    binary = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,  # NOT inverted
        11,  # block size (must be odd)
        2    # constant subtracted from mean
    )

    # Option 2: With light denoising (for slightly noisy documents)
    # Denoise first, then threshold
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    binary = cv2.threshold(
        denoised, 0, 255, 
        cv2.THRESH_BINARY + cv2.THRESH_OTSU  # NOT inverted
    )[1]

    # Option 3: If you need morphology (for very noisy scans)
    # Use MORPH_CLOSE on BLACK text, not white
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.threshold(
        blur, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU  # Black text on white
    )[1]
    # Now MORPH_CLOSE removes small BLACK noise (not white)
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))  # Smaller kernel
    # cleaned = cv2.morphologyEx(
    #     binary, 
    #     cv2.MORPH_CLOSE,  # Fills small black holes
    #     kernel, 
    #     iterations=1
    # )

    cv2.imshow('result', binary)
    cv2.waitKey()
    # image = cv2.imread(str(img_path))
    # gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # # blur = cv2.GaussianBlur(gray, (3, 3), 0)
    # # thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    # opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    # invert = 255 - opening

    # cv2.imshow('invert - 2', invert)
    # cv2.waitKey()

    # doc_name = str(img_path)[:-3] + "pdf"
    # pix.pdfocr_save(doc_name, language="mkd")
    # print(doc_name)
    # new_doc = pymupdf.open(doc_name)
    # page = new_doc[0]
    # block = page.get_text("blocks", sort=True)
    # block = page.get_text("text", sort=True)
    # block = re.sub('\n', '  ', block) #It is necessary to map it to more than just 1 space (2 or higher)
    # block = re.sub(r' {2,}', '\n', block)
    # # block = re.sub(' +', '', block)
    # block = block.split("\n")
    # print(f"{block=}\n\n")

    # for image_index, img in enumerate(image_list, start=1): # enumerate the image list
    #     xref = img[0] # get the XREF of the image
    #     pix = pymupdf.Pixmap(doc, xref) # create a Pixmap

    #     if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
    #         pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

    #     img_path = f"{image_output_folder_path_obj.absolute()}/page_{0}-image_{image_index}.png"
    #     pix.save(str(img_path)) # save the image as png
    #     pix = None
    #     img = Image.open(img_path)
    #     text2 = pytesseract.image_to_string(img, lang = "mkd", config="--psm 6")
    #     print(text2)
    # print(f"Page size: {page.rect}")
    # print(f"Has text layer: {bool(page.get_text().strip())}")
    
    # # Method 1: PyMuPDF OCR (your original attempt)
    # print("\n=== Method 1: PyMuPDF OCR ===")
    # try:
    #     tp = page.get_textpage_ocr(
    #         tessdata=str(Path(tesseract_path) / "tessdata"),
    #         language="mkd",
    #         dpi=300
    #     )
    #     text1 = page.get_text(textpage=tp, sort=True)
    #     print(f"Result length: {len(text1)}")
    #     print(f"Preview: {text1[:200] if text1 else 'EMPTY'}")
    # except Exception as e:
    #     print(f"Error: {e}")
    #     text1 = ""
    
    # Method 2: Convert to image and use pytesseract directly
    # print("\n=== Method 2: Image + Pytesseract ===")
    # try:
    #     # Render page at high resolution
    #     mat = pymupdf.Matrix(300/72, 300/72)  # 300 DPI
    #     pix = page.get_pixmap(matrix=mat)
        
    #     # Save temporarily
    #     img_path = root_folder_path_obj / "temp_page.png"
    #     pix.save(str(img_path))
        
    #     # OCR with pytesseract
    #     img = Image.open(img_path)
    #     text2 = pytesseract.image_to_string(img, lang='mkd', config='--psm 6')
        
    #     print(f"Result length: {len(text2)}")
    #     print(f"Preview: {text2 if text2 else 'EMPTY'}")
    #     # print(f"Preview: {text2[:200] if text2 else 'EMPTY'}")
        
    #     # Clean up
    #     img_path.unlink()
        
    # except Exception as e:
    #     print(f"Error: {e}")
    #     import traceback
    #     traceback.print_exc()
    #     text2 = ""
    
    # # Method 3: Try with English as fallback
    # print("\n=== Method 3: English OCR (fallback) ===")
    # try:
    #     mat = pymupdf.Matrix(300/72, 300/72)
    #     pix = page.get_pixmap(matrix=mat)
    #     img_path = root_folder_path_obj / "temp_page_eng.png"
    #     pix.save(str(img_path))
        
    #     img = Image.open(img_path)
    #     text3 = pytesseract.image_to_string(img, lang='eng', config='--psm 6')
        
    #     print(f"Result length: {len(text3)}")
    #     print(f"Preview: {text3[:200] if text3 else 'EMPTY'}")
        
    #     img_path.unlink()
        
    # except Exception as e:
    #     print(f"Error: {e}")
    #     text3 = ""
    
    # doc.close()
    
    # # Return the best result
    # results = [text1, text2, text3]
    # best_result = max(results, key=len)
    
    # print(f"\n=== BEST RESULT (length: {len(best_result)}) ===")
    # print(best_result[:500] if best_result else "No text extracted")
    
    # return best_result

if __name__ == "__main__":
    main()