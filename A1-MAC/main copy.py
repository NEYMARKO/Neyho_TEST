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

# DOC_NAME_TO_TYPE_MAP = {
#     "Договор за засновање претплатнички однос за користење": DocType.TYPE_1,
#     "Договор за купопродажба на уреди со одложено плаќање на рати": DocType.TYPE_2,
#     "Договор за користење на јавни комуникациски услуги": DocType.TYPE_3,
#     "Договор за користење на јавни комуникациски услуги ---- CHANGE MEEEEEE": DocType.TYPE_4,
#     "БАРАЊЕ ЗА ПРЕНЕСУВАЊЕ НА УСЛУГИ ПОМЕЃУ РАЗЛИЧНИ БАН БРОЕВИ КОИ ПРИПАЃААТ НА ИСТ ПРЕТПЛАТНИК": DocType.TYPE_5
# }


class VisualDebugger:
    def __init__(self):
        return
    def plot_img(self):
        return
    def draw_img(self):
        return

    def split_document_with_rectangular_contours(self, img_path : str, section_cnt : int, direction : int = 0) -> None:
        img = cv2.imread(img_path)
        width = img.shape[1]
        height = img.shape[0]
        horizontal_contour_rects = []
        vertical_contour_rects = []
        for i in range(1, section_cnt):
            x_low = int(width * ((i - 1) / section_cnt))
            x_high = int(width * (i / section_cnt))
            y_low = int(height * ((i - 1) / section_cnt))
            y_high = int(height * (i / section_cnt))
            rect = np.array(
                [
                (0, y_low),
                (width, y_low),
                (width, y_high),
                (0, y_high)
                ],
                dtype=np.int32
            ).reshape(-1,1,2)
            horizontal_contour_rects.append(rect)
            rect = np.array(
                [
                (x_low, 0),
                (x_high, 0),
                (x_high, height),
                (x_low, height)
                ],
                dtype=np.int32
            ).reshape(-1,1,2)
            vertical_contour_rects.append(rect)
        cv2.drawContours(img, horizontal_contour_rects if not direction else vertical_contour_rects, -1, (0, 0, 255), 8)
        cv2.imwrite(img_path[:-4] + "contours.png", img)
        return


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
    rotated = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if not dest_folder.exists() and not dest_folder.is_dir():
        dest_folder.mkdir(parents=True, exist_ok=True)
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

    return match

def customize_regex(content : str, info_of_interest : str, doc_type : hc.DocType) -> str:
    doc_regex_obj =  hc.DOCUMENT_REGEXES.get(doc_type, {}).get(info_of_interest, {})
    ocr_phrase_version = get_ocr_version_of_key_phrase(doc_regex_obj.get("preceding", ""), content)
    return ocr_phrase_version + doc_regex_obj.get("delimiter", "") + doc_regex_obj.get("unchanged", "")

#USED FOR OCR (FOR NOW)
def extract_scanned_pdf_data(img_path : Path, doc : pymupdf.Document, doc_type : hc.DocType, file_basename : str) -> dict:
    result = {hc.CONTRACT_DATE_STRING: "", hc.BAN_STRING: "", hc.EMBG_EDB_STRING: "", hc.RESIDENT_CUSTOMER_STRING: False, hc.BUSINESS_CUSTOMER_STRING: False}
    # print(f"{CONFIG.get(doc_type, {}).get("has_checkbox")=}")
    document_content = extract_content_from_page(doc[0])
    if hc.CONFIG.get(doc_type, {}).get("has_checkbox"):
        checkbox_content = get_checkbox_content(img_path, plot=False)
        result[hc.RESIDENT_CUSTOMER_STRING] = checkbox_content.get(hc.RESIDENT_CUSTOMER_STRING)
        result[hc.BUSINESS_CUSTOMER_STRING] = checkbox_content.get(hc.BUSINESS_CUSTOMER_STRING)
        # print(f"{checkbox_content=}")
    else:
        # print("DOESN'T HAVE CHECKBOXES")
        # Only Type 2 doesn't have checkbox for customer_type => special logic for it
        regex_expression = customize_regex(document_content, "customer_type" ,doc_type)
        # print(f"REGEX EXPRESSION: {regex_expression}")
        customer_type_match = re.search(regex_expression, document_content, re.DOTALL)
        if customer_type_match:
            try:
                matched_string = customer_type_match.group(1)
            except IndexError:
                matched_string = customer_type_match.group(0)
            # print(f"{fuzz.ratio(matched_string, "физичко лице")=}")
            is_resident = True if fuzz.ratio(matched_string, RESIDENT_KEYWORD) > 75 else False
            # print(f"{matched_string=}")
            result[hc.RESIDENT_CUSTOMER_STRING] = is_resident
            result[hc.BUSINESS_CUSTOMER_STRING] = not is_resident
    table_content = ""
    if hc.CONFIG.get(doc_type, {}).get("has_table_bounds"):
        table_content = get_table_content(img_path, file_basename)
        # print(f"{table_content=}")
    else:
        table_content = document_content
    # print(f"{document_content=}")
    # print(f"{table_content=}")
    result[hc.CONTRACT_DATE_STRING] = get_date(document_content)
    result[hc.BAN_STRING] = get_number(9, 9, document_content)
    if hc.CONFIG.get(doc_type, {}).get("ambiguous_embg"):
        regex_expression = customize_regex(table_content, hc.EMBG_EDB_STRING , doc_type)
        embg_edb_match = re.search(regex_expression, table_content, re.DOTALL)
        if embg_edb_match:
            matched_string = embg_edb_match.group(1)
            # print(f"EMBG_EDB MATCH: {matched_string}")
            result[hc.EMBG_EDB_STRING] = matched_string
    else:
        result[hc.EMBG_EDB_STRING] = get_number(13, 13, table_content)
    return result

def checkbox_fallback(page : pymupdf.Page, doc_type : hc.DocType) -> dict:
    img_path = extract_img_from_pdf_page(page, f"doc_type_{doc_type}_temp_checkbox.png")
    return get_checkbox_content(img_path, plot=False)

#USED FOR REGULAR PDF (FOR NOW)
def extract_data(doc : pymupdf.Document, doc_type : hc.DocType) -> dict:
    content = extract_content_from_page(doc[0])
    # print(f"{content=}")
    result = {hc.CONTRACT_DATE_STRING: "", hc.BAN_STRING: "", hc.EMBG_EDB_STRING: "", hc.RESIDENT_CUSTOMER_STRING: False, hc.BUSINESS_CUSTOMER_STRING: False}
    for expression in hc.DOCUMENT_REGEXES.get(doc_type, {}).get(hc.CONTRACT_DATE_STRING, []):
        match = re.search(expression, content, re.DOTALL)
        if match:
            result[hc.CONTRACT_DATE_STRING] = match.group(0)
    ban_match = re.search(hc.DOCUMENT_REGEXES.get(doc_type, {}).get(hc.BAN_STRING, ""), content, re.DOTALL)
    if ban_match:
        try:
            result[hc.BAN_STRING] = ban_match.group(1)
        except IndexError:
            result[hc.BAN_STRING] = ban_match.group(0)
    embg_edb_match = re.search(hc.DOCUMENT_REGEXES.get(doc_type, {}).get(hc.EMBG_EDB_STRING, ""), content, re.DOTALL)
    if embg_edb_match:
        try:
            result[hc.EMBG_EDB_STRING] = embg_edb_match.group(1)
        except IndexError:
            result[hc.EMBG_EDB_STRING] = embg_edb_match.group(0)
    customer_type_match = re.search(hc.DOCUMENT_REGEXES.get(doc_type, {}).get("customer_type", ""), content, re.DOTALL)
    if customer_type_match:
        matched_string = customer_type_match.group(0).strip().lower()
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


def extract_img_from_pdf_page(page : pymupdf.Page, file_name : str) -> Path:
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
    # root_folder_path_obj = Path(__file__).parent / "INPUT/TYPE_1/DEBUG"
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
                img_path = extract_img_from_pdf_page(doc[0], name)
                rotated_path = straightenImage(img_path, Path(__file__).parent / f"rotated_imgs/document_{i}")
                doc = scanned_img_to_pdf(doc[0], Path(__file__).parent / "scanned_img_to_pdf" / f"TYPE_{doc_type.value}" / name, "scanned_img.pdf")
                result = extract_scanned_pdf_data(img_path, doc, doc_type, name) 
                # result = extract_scanned_pdf_data(rotated_path, doc, doc_type, name) 
            else:
                result = extract_data(doc, doc_type)
            if not doc:
                raise RuntimeError("Unable to read document!")
            print(f"\n{result=}\n")
            i += 1
    return

if __name__ == "__main__":
    main()