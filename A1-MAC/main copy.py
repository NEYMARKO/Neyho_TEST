import re
import cv2
import fitz
import pymupdf
import numpy as np
from PIL import Image
from pathlib import Path
from boxdetect import config
import hardcoded_config as hc
from rapidfuzz import process, fuzz
from boxdetect.pipelines import get_checkboxes
from table_content_extractor import TableExtractor

regs = {'3': [
    r'бр\.\s*(\d+)',
    r'на ден\s+(\b[0-9\.]*\b)\s+помеѓу',
    r'(?<=ПРЕТПЛАТНИК)(.*)(?=правно лице)',
    r'ЕМБГ:\s+(\b[0-9]+\b)'
    ]}

RESIDENT_KEYWORD = "физичко лице"

def straightenImage(img_path : Path, dest_folder : Path) -> Path:
    data = np.fromfile(img_path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=50, maxLineGap=10)

    (h, w) = image.shape[:2]
    min_length = 0.1 * w

    filtered_lines = []
    angles = []

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length > min_length:
                # Calculate the angle of the line
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if -45 <= angle <= 45:  # Near-horizontal lines only
                    filtered_lines.append((x1, y1, x2, y2, length))
                    angles.append((angle, length))

    # Calculate the weighted average angle of the filtered lines
    if angles:
        total_weight = sum(weight for _, weight in angles)
        average_angle = sum(angle * weight for angle, weight in angles) / total_weight
    else:
        average_angle = 0  # No lines detected, assume no rotation needed
    # Rotate the image based on the average angle
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, average_angle, 1.0)
    rotated = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    if not dest_folder.exists() and not dest_folder.is_dir():
        dest_folder.mkdir(parents=True, exist_ok=True)
    # rotated = cv2.rotate(rotated, cv2.ROTATE_90_CLOCKWISE)
    save_path = dest_folder / "rotated.png"
    # cv2.imwrite(str(save_path), rotated)
    img = Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY))
    img.save(save_path, dpi=(300, 300))
    return save_path

def extract_content_from_page(page : pymupdf.Page) -> str:
    text = str(page.get_text("text", sort=True))
    text = re.sub('\n', '  ', text) #It is necessary to map it to more than just 1 space (2 or higher)
    text = re.sub(r' {2,}', ' ', text)
    # print(f"{text=}")
    return text

def raw_img_to_pdf(img_src : Path, dest_folder : Path, file_name : str) -> pymupdf.Document:
    doc = fitz.open()
    imgdoc = fitz.open(str(img_src))
    pdfbytes = imgdoc.convert_to_pdf()
    imgpdf = fitz.open("pdf", pdfbytes)
    doc.insert_pdf(imgpdf)
    if not dest_folder.exists() and not dest_folder.is_dir():
        dest_folder.mkdir(parents=True, exist_ok=True)
    doc.save(str(dest_folder / file_name))
    return scanned_img_to_pdf(doc[0], dest_folder, file_name)

def scanned_img_to_pdf(page : pymupdf.Page, dest_folder : Path, file_name : str) -> pymupdf.Document:
    image_list = page.get_images()
    if not image_list:
        raise RuntimeError("Unable to locate images on a page")
    matrix = pymupdf.Matrix(4, 4)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    if pix.alpha:
        pix.set_alpha(None)
    if not dest_folder.exists() and not dest_folder.is_dir():
        dest_folder.mkdir(parents=True, exist_ok=True)
    doc_path = str(dest_folder / file_name)
    pix.pdfocr_save(doc_path, language="mkd")
    return pymupdf.open(str(doc_path))


def get_relevant_pair(sorted_checkboxes : list[any]) -> list:
    """
    If width and height ranges are too broad, more than just checkboxes could get detected.
    Function is used to determine whether detected stuff (that is considered to be checkbox)
    is on the same level (approximately same height) as it's follower in the list
    """
    # checkbox_bounds = DOCUMENT_LAYOUT.get(doc_type, {}).get("checkbox", [])
    # lower_y_bound = checkbox_bounds[0][1]
    pair = []
    while len(sorted_checkboxes) > 1:
        bound1 = sorted_checkboxes[0][0]
        bound2 = sorted_checkboxes[1][0]
        #if it is more than 20 pixels of height difference, they probably aren't in the same line
        if abs(bound1[1] - bound2[1]) > 20 or abs(bound1[3] - bound2[3]) > 20:
            # or sorted_checkboxes[0][0][1] < height * lower_y_bound: #can't really rely on bounds since image can be
            # larger than just content of document - it can have padding (which could be large)
            sorted_checkboxes = sorted_checkboxes[1:]
        else:
            pair = [sorted_checkboxes[0], sorted_checkboxes[1]]
            break
    pair = sorted(pair, key=lambda el : el[0][0], reverse=False)
    return pair

def get_checkbox_content(img_path : Path, plot : bool = False) -> dict[str, bool]:
    """
    In case of not detecting checkboxes, check width and height range of
    checkboxes in image -> can use any image viewer => good one: https://pixspy.com/ 
    """
    # img_path = str(crop_page(page, doc_type, 'checkbox').absolute())
    cfg = config.PipelinesConfig()
    cfg.width_range = (30, 55)      # Adjust based on actual checkbox size
    cfg.height_range = (25, 40)     # Should be similar to width for square boxes
    cfg.scaling_factors = [1.3, 1.4, 1.5]
    cfg.wh_ratio_range = (0.8, 1.2)  # Closer to square
    cfg.group_size_range = (1, 1)
    cfg.dilation_iterations = 0      # This can merge the double borders
    
    checkboxes = get_checkboxes(
        str(img_path), cfg=cfg, px_threshold=0.1, plot=False, verbose=False
    )

    if plot:
        import matplotlib.pyplot as plt
        from boxdetect.pipelines import get_boxes
        rects, grouping_rects, image, output_image = get_boxes(
            str(img_path), cfg=cfg, plot=False
        )
        plt.figure(figsize=(20,20))
        plt.imshow(output_image)
        plt.show()
        for checkbox in checkboxes:
            print(f"Bounding rectangle: {checkbox[0]}")
            print(f"Result of 'constains_pixels' for the checkbox: {checkbox[1]}")
            plt.figure(figsize=(1,1))
            plt.imshow(checkbox[2])
            plt.show()

    # print(f"{checkboxes.size=}")
    if checkboxes.size == 0:
        print("Unable to detect checkboxes, check cfg.width and height range")
        return {}
    elif checkboxes.size / 3 == 1:
        print("Only 1 checkbox detected")
        return {}
    
    #Sort first by y coordinate - those higher in document come first,
    #then sort by x coordinate - those that are more left come first
    sorted_checkboxes = sorted(checkboxes.tolist(), key=lambda inner_l: inner_l[0][1], reverse=False)
    # print(f"{sorted_checkboxes=}")
    pair = get_relevant_pair(sorted_checkboxes)
    # print(f"{pair=}")
    is_resident = pair[0][1]
    return {hc.RESIDENT_CUSTOMER_STRING : is_resident, hc.BUSINESS_CUSTOMER_STRING : not is_resident}

def get_table_content(img_path : Path, file_basename : str) -> str:
    # img_path = crop_page(page, doc_type, 'table')
    # print(f"{str(img_path)=}")
    tableExtractor = TableExtractor(img_path, file_basename)
    img_save_path = Path(__file__).parent / f"tables/{file_basename}/cleared_table.png"
    tableExtractor.clear_table(img_save_path)
    # result_img_path = tableExtractor.result_path if CONFIG.get(doc_type, {}).get("clear_table") else img_path 
    # doc = raw_img_to_pdf(result_img_path, Path(__file__).parent / "raw_img_to_pdf" / file_basename, "raw_img.pdf")
    doc = raw_img_to_pdf(img_save_path, Path(__file__).parent / "raw_img_to_pdf" / file_basename, "raw_img.pdf")
    return extract_content_from_page(doc[0])

def get_date(file_content : str) -> str:
    date_string = ""
    for date_format in hc.DATE_REGEXES:
        match = re.search(date_format, file_content, re.DOTALL)
        # print(f"{match=}")
        if match:
            date_string = match.group(0).strip()
            break
    if ',' in date_string:
        date_string = date_string.replace(',', '.')
    if '-' in date_string:
        date_string = date_string.replace('-', '.')
    return date_string

def get_number(digit_cnt_low : int, digit_cnt_high : int, content : str) -> str:
    expressions = [
        "\\s\\d{" + str(digit_cnt_low) + "," + str(digit_cnt_high) + "}\\s",
        "\\s\\d{" + str(digit_cnt_low) + "," + str(digit_cnt_high) + "}\\.\\s",
        "\\s\\d{" + str(digit_cnt_low) + "," + str(digit_cnt_high) + "}\\,\\s",
    ]
    # print(f"{expression=}")
    for expression in expressions:
        match = re.search(expression, content, re.DOTALL)
        # print(f"CONTENT TO MATCH: {content}")
        if match:
            # print(f"Number match: {match}")
            return match.group(0).strip().replace('.', '').replace(',', '')
    return ""

def get_ocr_version_of_key_phrase(phrase : str, content : str) -> str:
    words = content.split()
    kw_len = len(phrase.split())

    ngrams = [" ".join(words[i:i+kw_len]) for i in range(len(words) - kw_len + 1)]

    # print(f"{ngrams=}")
    match, score, idx = process.extractOne(phrase, ngrams)
    # print(f"Matched {phrase} with {match} => score: {score}")

    return match if score > 70 else ""

def customize_regex(content : str, doc_regex_obj : dict) -> str:
    ocr_phrase_version = get_ocr_version_of_key_phrase(doc_regex_obj.get("preceding", ""), content)
    return ocr_phrase_version + doc_regex_obj.get("unchanged", "")


def get_regex_match(regex : str, content : str) -> str:
    match = re.search(regex, content, re.DOTALL)
    if match:
        try:
            return match.group(1)
        except IndexError:
            return match.group(0)
    return ""

def find_info_with_regex(relevant_info : str, content : str, document_regexes : dict, modify_regex : bool = False) -> str:
    regex_expr = document_regexes.get(relevant_info, None)
    reg = ""
    if not regex_expr:
        return ""
    if isinstance(regex_expr, list):
        for reg in regex_expr:
            if modify_regex:
                reg = customize_regex(content, reg)
            # matched_string = re.search(reg, content, re.DOTALL)
            # print(f"customized regex: {reg}")
            matched_string = get_regex_match(reg, content)
            if matched_string:
                return matched_string
    elif isinstance(regex_expr, str):
        if modify_regex:
            regex_expr = customize_regex(content, document_regexes)
        return get_regex_match(regex_expr, content)
    elif isinstance(regex_expr, dict):
        if modify_regex:
            reg = customize_regex(content, regex_expr)
        else:
            reg = regex_expr.get(hc.PRECEDING_STRING, "") + regex_expr.get(hc.UNCHANGED_STRING, "")
        # print(f"reg for {relevant_info}: {reg}")
        return get_regex_match(reg, content)
    return ""

#USED FOR OCR (FOR NOW)
def extract_ocr_data(img_path : Path, doc : pymupdf.Document, doc_type : hc.DocType, file_basename : str) -> dict:
    document_regexes = hc.OCR_DOCUMENT_REGEXES.get(doc_type, None)
    if not document_regexes:
        print("No defined regexes for this document type")
        return {}
    result = {hc.CONTRACT_DATE_STRING: "", hc.BAN_STRING: "", hc.EMBG_EDB_STRING: "", hc.RESIDENT_CUSTOMER_STRING: None, hc.BUSINESS_CUSTOMER_STRING: None}
    # print(f"{CONFIG.get(doc_type, {}).get("has_checkbox")=}")
    document_content = extract_content_from_page(doc[0])
    # print(f"{document_content=}")
    if hc.CONFIG.get(doc_type, {}).get("has_checkbox"):
        checkbox_content = get_checkbox_content(img_path, plot=False)
        result[hc.RESIDENT_CUSTOMER_STRING] = checkbox_content.get(hc.RESIDENT_CUSTOMER_STRING)
        result[hc.BUSINESS_CUSTOMER_STRING] = checkbox_content.get(hc.BUSINESS_CUSTOMER_STRING)
        # print(f"{checkbox_content=}")
    else:
        #ONLY TYPE_2 AND TYPE_4 DON'T HAVE CHECKBOXES
        customer_type_matched_string = find_info_with_regex(hc.CUSTOMER_TYPE_STRING, document_content[:int(len(document_content) * 0.2)], 
                                                            document_regexes, modify_regex=True)
        if (doc_type == hc.DocType.TYPE_2):
            resident_score = fuzz.ratio(customer_type_matched_string, document_regexes.get(hc.RESIDENT_CUSTOMER_STRING, ""))
            business_score = fuzz.ratio(customer_type_matched_string, document_regexes.get(hc.BUSINESS_CUSTOMER_STRING, ""))
            is_resident = False
            is_business = False
            if (resident_score > business_score and resident_score > 70):
                is_resident = True
                is_business = False
            elif (business_score > resident_score and business_score > 70):
                is_resident = False
                is_business = True
            result[hc.RESIDENT_CUSTOMER_STRING] = is_resident
            result[hc.BUSINESS_CUSTOMER_STRING] = is_business
            # print(f"{resident_score=}, {business_score=}")
        else:
            # print("HERE")
            for reg in document_regexes.get(hc.CUSTOMER_TYPE_STRING, []):
                # reg_expr = customize_regex(hc.CUSTOMER_TYPE_STRING, document_content[:int(len(document_content) * 0.2)], document_regexes)
                matched_string = get_regex_match(reg, document_content)
                if matched_string:
                    print(f"in customer type: {matched_string=}")
    table_content = ""
    if hc.CONFIG.get(doc_type, {}).get("has_table_bounds"):
        table_content = get_table_content(img_path, file_basename)
        # print(f"{table_content=}")
    else:
        table_content = document_content
    result[hc.CONTRACT_DATE_STRING] = get_date(document_content)
    ban_matched_string = find_info_with_regex(hc.BAN_STRING, document_content, document_regexes, modify_regex=True)
    result[hc.BAN_STRING] = ban_matched_string
    emdg_edb_matched_string = find_info_with_regex(hc.EMBG_EDB_STRING, table_content, document_regexes, modify_regex=True)

    result[hc.EMBG_EDB_STRING] = emdg_edb_matched_string
    return result

def checkbox_fallback(page : pymupdf.Page, doc_type : hc.DocType) -> dict:
    img_path = extract_img_from_pdf_page(page, f"doc_type_{doc_type}_temp_checkbox.png")
    return get_checkbox_content(img_path, plot=False)

#USED FOR REGULAR PDF (FOR NOW)
def extract_data(doc : pymupdf.Document, doc_type : hc.DocType) -> dict:
    document_regexes = hc.DOCUMENT_REGEXES.get(doc_type, None)
    if not document_regexes:
        print("Unable to find document regexes")
        return {}
    content = extract_content_from_page(doc[0])
    # print(f"{content=}")
    result = {hc.CONTRACT_DATE_STRING: "", hc.BAN_STRING: "", hc.EMBG_EDB_STRING: "", hc.RESIDENT_CUSTOMER_STRING: None, hc.BUSINESS_CUSTOMER_STRING: None}
    date_matched_string = find_info_with_regex(hc.CONTRACT_DATE_STRING, content, document_regexes)
    if date_matched_string:
        result[hc.CONTRACT_DATE_STRING] = date_matched_string
    ban_matched_string = find_info_with_regex(hc.BAN_STRING, content, document_regexes)
    if ban_matched_string:
        result[hc.BAN_STRING] = ban_matched_string
    embg_edb_matched_string = find_info_with_regex(hc.EMBG_EDB_STRING, content, document_regexes)
    if embg_edb_matched_string:
        result[hc.EMBG_EDB_STRING] = embg_edb_matched_string
    
    if doc_type == hc.DocType.TYPE_4:
        regexes = document_regexes.get(hc.CUSTOMER_TYPE_STRING, [])
        if len(regexes) == 0:
            print(f"No customer_type regexes defined for doc_type: {doc_type}")
        else:
            reg1 = regexes[0]
            reg2 = regexes[1]
            match1 = get_regex_match(reg1, content).strip()
            match2 = get_regex_match(reg2, content).strip()

            # print(f"{match1=}, {match2=}")
            is_resident = False
            is_business = False
            if match1 and not match2:
                is_resident = True
                is_business = False
            elif not match1 and match2:
                is_resident = False
                is_business = True
            result[hc.RESIDENT_CUSTOMER_STRING] = is_resident
            result[hc.BUSINESS_CUSTOMER_STRING] = is_business

    else:
        customer_type_matched_string = find_info_with_regex(hc.CUSTOMER_TYPE_STRING, content, document_regexes)
        if customer_type_matched_string:
            matched_string = customer_type_matched_string.lower().strip()
            # print(f"{matched_string=}")
            is_resident = False
            possible_check_marks = [chr(0x455), chr(0x78), chr(0x2713), chr(0x2714), chr(0x1F5F8), chr(0x2611), chr(0x1F5F9), chr(0x10102)]
            all_mark_positions = [matched_string.find(possible_check_marks[i]) for i in range(len(possible_check_marks))]
            # print(f"{all_mark_positions=}")
            if all(var == -1 for var in all_mark_positions):
                # print("GOING FOR FALLBACK")
                checkbox_result = checkbox_fallback(doc[0], doc_type)
                # print(f"{checkbox_result=}")
                if not checkbox_result:
                    # raise ValueError("Unable to detect checked box")
                    print("UNABLE TO DETECT CHECKBOXES")            
                else:
                    result[hc.RESIDENT_CUSTOMER_STRING] = checkbox_result.get(hc.RESIDENT_CUSTOMER_STRING)
                    result[hc.BUSINESS_CUSTOMER_STRING] = checkbox_result.get(hc.BUSINESS_CUSTOMER_STRING)
            else:
                is_resident = any(var == 0 for var in all_mark_positions)
                result[hc.RESIDENT_CUSTOMER_STRING] = is_resident
                result[hc.BUSINESS_CUSTOMER_STRING] = not is_resident
    return result


def extract_img_from_pdf_page(page : pymupdf.Page, file_name : str, preprocess : bool = False) -> Path:
    """
    Extracts and saves image contained in pdf page and saves them in <root>/extracted_imgs folder
    DPI needs to 300 (ocr engines assume 300 dpi)
    :param page: Description
    :type page: pymupdf.Page
    :param file_name: Description
    :type file_name: str
    :return: Description
    :rtype: Path
    """
    if file_name.endswith(".pdf"):
        file_name = file_name[:-4]
    dest_folder = Path(__file__).parent / f"extracted_imgs/{file_name}"
    image_list = page.get_images()
    if not image_list:
        raise RuntimeError("Unable to locate images on a page")
    #PDF uses points, not pixels => 1 point = 1/72 inch => 1 Inch = 72 PDF points
    #DPI - 'Dots Per Inch' - measures density of dots (or pixels) in image or an display
    # => dpi = pixels per inch, 1 inch has 72 points => dpi = pixels per 72 points => pixels = dpi / 72points
    #PDF page width in points * scale = pixel width
    dpi = 300
    scale = dpi / 72 #because PDF uses 72 points per inch
    matrix = pymupdf.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    if pix.alpha:
        pix.set_alpha(None)
    # pix.save(str(dest))
    if not dest_folder.exists() and not dest_folder.is_dir():
        dest_folder.mkdir(parents=True, exist_ok=True)
    img_path = dest_folder / "extracted.png"
    # print(f"{img_path=}")
    if preprocess:
        kernel_size = 10
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        cv2.imwrite(str(img_path.parent / "binary_mask.png"), binary_mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        expanded_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
        expanded_mask = cv2.dilate(expanded_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (11,11)), iterations=20)
        cv2.imwrite(str(img_path.parent / "expanded_mask.png"), expanded_mask)
        contours, _ = cv2.findContours(expanded_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            print("No non-white areas found")
            return Path()
        # print(f"{contours=}")
        original_image_with_all_contours = img.copy()
        cv2.drawContours(original_image_with_all_contours, contours, -1, (0, 255, 0), 3)
        cv2.imwrite(str(img_path.parent / "all_conturs.png"), original_image_with_all_contours)
        # Find the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        cv2.imwrite(str(img_path), img)
        x = max(x, 0)
        y = max(y, 0)
        w = min(w, img.shape[1] - x)
        h = min(h, img.shape[0] - y)
        
        # Crop the image based on the adjusted bounding box
        cropped_image = img[y:y + h, x:x + w]
        # orig_width, orig_height, channels = img.shape
        # cropped_width, cropped_height, cropped_channels = cropped_image.shape
        # aspect_ratio = cropped_width / orig_width if orig_width > orig_height else cropped_height / orig_height
        # cropped_image = cv2.resize(cropped_image, (int(orig_width * aspect_ratio), int(orig_height * aspect_ratio)), interpolation=cv2.INTER_LANCZOS4)
        upscaled = cv2.resize(cropped_image, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(str(img_path.parent / "upscaled.png"), upscaled)
        cropped_img_path = img_path.parent / "cropped.png"
        cv2.imwrite(str(cropped_img_path), cropped_image)
        if len(upscaled.shape) == 3:
            gray_upscaled = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        else:
            gray_upscaled = upscaled
        
        # Check polarity
        if np.mean(gray_upscaled) < 127:
            gray_upscaled = 255 - gray_upscaled
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray_upscaled, None, h=8, templateWindowSize=7, searchWindowSize=21)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Binarize (Otsu works well for small text after upscaling)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Double-check polarity
        if np.sum(binary == 0) > np.sum(binary == 255):
            binary = 255 - binary
        
        # Save preprocessed image
        cropped_img_path = img_path.parent / "cropped_preprocessed.png"
        cv2.imwrite(str(cropped_img_path), binary)
        return cropped_img_path
    else:
        pix.save(str(img_path))
    return img_path

def is_regular_pdf_page(page : pymupdf.Page) -> bool:
    """
    Checks whether page is computer generated pdf or scanned document
    
    :param page: Description
    :type page: pymupdf.Page
    :return: Description
    :rtype: bool
    """
    text_blocks = 0
    image_blocks = 0
    content = page.get_text("dict")
    for b in content.get('blocks', []):
        if (b['type'] == 0):
            text_blocks += 1
        elif (b['type'] == 1):
            image_blocks += 1
    # print(f"{text_blocks=}")
    # print(f"{image_blocks=}")
    return text_blocks > 0

def main():
    root_folder_path_obj = Path(__file__).parent / "INPUT/TYPE_2"
    # root_folder_path_obj = Path(__file__).parent / "INPUT/TYPE_4"
    i = 0
    for x in root_folder_path_obj.iterdir():
        if x.is_file() and x.name.endswith("pdf"):
            print(f"{"-" * 40}Processing file: {x.stem}{"-" * 40}")
            # doc_type = DOC_NAME_TO_TYPE_MAP.get(file_basename, DocType.UNDEFINED)
            doc_type = hc.DocType.TYPE_2
            doc = pymupdf.open(Path(root_folder_path_obj / x.name))
            result = None
            name = f"document_{i}"
            if not is_regular_pdf_page(doc[0]):
                img_path = extract_img_from_pdf_page(doc[0], name, preprocess=False)
                # print(f"Returned path: {str(img_path)}")
                # img = image = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                # cv2.imwrite(str(Path(__file__).parent / f"rotated_imgs/document_{i}/rotated.png"), img)
                rotated_path = straightenImage(img_path, Path(__file__).parent / f"rotated_imgs/document_{i}")
                doc = scanned_img_to_pdf(doc[0], Path(__file__).parent / "scanned_img_to_pdf" / f"TYPE_{doc_type.value}" / name, "scanned_img.pdf")
                result = extract_ocr_data(rotated_path, doc, doc_type, name) 
                # result = extract_ocr_data(img_path, doc, doc_type, name) 
            else:
                result = extract_data(doc, doc_type)
            if not doc:
                raise RuntimeError("Unable to read document!")
            print(f"\n{result=}\n")
            i += 1
    return

if __name__ == "__main__":
    main()