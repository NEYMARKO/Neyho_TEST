import cv2
import numpy as np
from pathlib import Path
from numpy.typing import NDArray
    
class TableExtractor:
    def __init__(self, image_path : Path, file_basename):
        self.original_image: cv2.typing.MatLike | None = cv2.imread(str(image_path))
        if self.original_image is None:
            raise FileNotFoundError(f"Couldn't read image: {str(image_path)}")
        height, width, channels = self.original_image.shape
        self.original_image = self.original_image[0:int(0.5 * height), 0:width]
        self.file_basename = file_basename

    def extract_table_with_fixed_perspective(self, save_path : Path) -> cv2.typing.MatLike | None:
        if not save_path.parent.exists() or not save_path.parent.is_dir():
            save_path.parent.mkdir(parents=True, exist_ok=True)
        preprocessed_image = self.preprocess_image()
        if preprocessed_image is None:
            return None
        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        # preprocessed_image = cv2.dilate(preprocessed_image, kernel, iterations=5)
        contour_with_max_area_ordered = self.find_rect_contour_with_max_area(preprocessed_image)
        if contour_with_max_area_ordered is None:
            print("No rectangle contours found")
            return None
        perspective_corrected_image = self.apply_perspective_transform(contour_with_max_area_ordered)
        preprocessed_image = self.preprocess_image(perspective_corrected_image)
        cv2.imwrite(str(save_path.parent / "perspective.png"), perspective_corrected_image)
        cv2.imwrite(str(save_path.parent / "rectangular_contours.png"), self.original_image_with_only_rectangular_contours)
        cv2.imwrite(str(save_path.parent / "contour_with_max_area.png"), self.original_image_with_contour_with_max_area)
        return perspective_corrected_image
    
    def clear_table(self, save_path : Path) -> None:
        self.save_path = save_path
        if not save_path.parent.exists() or not save_path.parent.is_dir():
            save_path.parent.mkdir(parents=True, exist_ok=True)
        # perspective_corrected_image = self.extract_table_with_fixed_perspective(save_path)
        # if perspective_corrected_image is None:
        #     print("Couldn't generate perspective image")
        #     return 
        # preprocessed_image = self.preprocess_image(perspective_corrected_image, use_gauss=False)
        preprocessed_image = self.preprocess_image()
        if preprocessed_image is None:
            return None
        contour_with_max_area_ordered = self.find_rect_contour_with_max_area(preprocessed_image)
        if contour_with_max_area_ordered is None:
            print("No rectangle contours found")
            return None
        cv2.imwrite(str(save_path.parent / "contour_with_max_area.png"), self.original_image_with_contour_with_max_area)
        top_left, top_right, bottom_right, bottom_left = contour_with_max_area_ordered
        lowest_x, lowest_y = top_left 
        highest_x, highest_y = bottom_right 
        if preprocessed_image is not None:
            self.remove_table_lines(preprocessed_image[int(lowest_y) : int(highest_y), int(lowest_x) : int(highest_x)])
            # self.remove_table_lines(preprocessed_image)
        cv2.imwrite(str(save_path.parent / "combined_lines.png"), self.combined_lines)
        cv2.imwrite(str(save_path), self.image_without_lines_noise_removed)
        return
    
    def preprocess_image(self, input_image : cv2.typing.MatLike | None = None, use_gauss : bool = False) -> cv2.typing.MatLike | None:
        image: cv2.typing.MatLike | None = (
            self.original_image if input_image is None else input_image
        )
        if image is None:
            return None 
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if use_gauss and image is not None:
            gray_img = cv2.GaussianBlur(gray_img, (3,3), 0)
        threshold_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        inverted_img = cv2.bitwise_not(threshold_img)
        return inverted_img

    def order_points(self, pts) -> NDArray[np.float32]:
        # initialzie a list of coordinates that will be ordered
        # such that the first entry in the list is the top-left,
        # the second entry is the top-right, the third is the
        # bottom-right, and the fourth is the bottom-left
        pts = pts.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
        # the top-left point will have the smallest sum, whereas
        # the bottom-right point will have the largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        # now, compute the difference between the points, the
        # top-right point will have the smallest difference,
        # whereas the bottom-left will have the largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        # return the ordered coordinates
        return rect

    def find_rect_contour_with_max_area(self, inverted_image : cv2.typing.MatLike) -> NDArray[np.float32] |  None:
        """
        1. Uses OpenCV to find all contours.
        2. Loops through the countours and leaves only the rectangular ones.
        3. Finds the largest contour by area - is presumed to be the table.
        """
        # Assert should only be used in debug, but since I am raising error in the constructor,
        # it won't do any harm but will remove red underlines in .copy() function call
        assert self.original_image is not None
        # Find all contours in the image and draw them over original_image
        inverted_image = self.extract_horizontal_and_vertical_lines(inverted_image, use_final_dilate=True)
        cv2.imwrite(str(self.save_path.parent / "inverted_image.png"), inverted_image)
        contours, hierarchy = cv2.findContours(inverted_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        original_image_with_all_contours = self.original_image.copy()
        cv2.drawContours(original_image_with_all_contours, contours, -1, (0, 255, 0), 3)
        cv2.imwrite(str(self.save_path.parent / "all_contours.png"), original_image_with_all_contours)
        # Filter contours and leave only rectangular ones
        rectangular_contours = []
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                rectangular_contours.append(approx)
        self.original_image_with_only_rectangular_contours = self.original_image.copy()
        cv2.drawContours(self.original_image_with_only_rectangular_contours, rectangular_contours, -1, (0, 255, 0), 3)
        cv2.imwrite(str(self.save_path.parent / "rectangular_contours.png"), self.original_image_with_only_rectangular_contours)
        # Find largest contour by area (in the list of all rectangular contours)
        max_area = 0
        contour_with_max_area = None
        for contour in rectangular_contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                max_area = area
                contour_with_max_area = contour
        self.original_image_with_contour_with_max_area = self.original_image.copy()
        if contour_with_max_area is None:
            return None
        x, y, w, h = cv2.boundingRect(contour_with_max_area)
        rect = np.array([
            [x, y],           # top-left: min x, min y
            [x + w, y],       # top-right: max x, min y
            [x + w, y + h],   # bottom-right: max x, max y
            [x, y + h]        # bottom-left: min x, max y
        ], dtype=np.float32)

        # cv2.drawContours(self.original_image_with_contour_with_max_area, [contour_with_max_area], -1, (0, 255, 0), 3)
        cv2.drawContours(self.original_image_with_contour_with_max_area, [rect.astype(np.int32)], -1, (0, 255, 0), 3)
        return self.order_points(contour_with_max_area)

    def calculate_new_width_and_height_of_image(self, contour_with_max_area_ordered) -> tuple[float, float]:
        top_left, top_right, bottom_right, bottom_left = contour_with_max_area_ordered

        width_top = np.linalg.norm(top_right - top_left)
        width_bottom = np.linalg.norm(bottom_right - bottom_left)
        height_left = np.linalg.norm(bottom_left - top_left)
        height_right = np.linalg.norm(bottom_right - top_right)

        target_width = int(max(width_top, width_bottom))
        target_height = int(max(height_left, height_right))
        return (target_width, target_height)

    def apply_perspective_transform(self, contour_with_max_area_ordered) -> cv2.typing.MatLike:
        new_width, new_height = self.calculate_new_width_and_height_of_image(contour_with_max_area_ordered)
        pts1 = np.float32(contour_with_max_area_ordered)
        pts2 = np.float32([
            [0, 0], 
            [new_width - 1, 0], 
            [new_width - 1, new_height - 1], 
            [0, new_height - 1]]
        )
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        perspective_corrected_image = cv2.warpPerspective(
            self.original_image, 
            matrix, 
            (new_width, new_height), 
            flags=cv2.INTER_CUBIC,  # ✅ Better for text
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        kernel_sharpen = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])
        perspective_corrected_image = cv2.filter2D(perspective_corrected_image, -1, kernel_sharpen)
        return perspective_corrected_image
    # Below are helper functions
    def calculateDistanceBetween2Points(self, p1, p2):
        dis = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        return dis

    def extract_horizontal_and_vertical_lines(self, inverted_image : cv2.typing.MatLike, use_final_dilate : bool = False) -> cv2.typing.MatLike:
        # Erode everything that isn't horizontal line of length 20px
        # Dilate result to make it thicker
        # Product are table horizontal bounds
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))
        horizontal_lines = cv2.erode(inverted_image, horizontal_kernel, iterations=5)
        horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=10)
        # horizontal_lines = cv2.morphologyEx(inverted_image, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Erode everything that isn't vertical line of length 20px
        # Dilate result to make it thicker
        # Product are table vertical bounds
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        vertical_lines = cv2.erode(inverted_image, vertical_kernel, iterations=5)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=10)
        # vertical_lines = cv2.morphologyEx(inverted_image, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Combine vertical and horiziontal lines into new image
        all_lines = cv2.add(horizontal_lines, vertical_lines)
        if use_final_dilate:
            all_lines = cv2.dilate(all_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3,3)), iterations=3)
        cv2.imwrite(str(self.save_path.parent / "extracted_lines.png"), all_lines)
        return all_lines
    # def extract_horizontal_and_vertical_lines(self, inverted_image: cv2.typing.MatLike) -> cv2.typing.MatLike:
    #     # Extract horizontal lines
    #     horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
    #     horizontal_lines = cv2.erode(inverted_image, horizontal_kernel, iterations=5)
    #     horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=10)
        
    #     # Extract vertical lines
    #     vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    #     vertical_lines = cv2.erode(inverted_image, vertical_kernel, iterations=5)
    #     vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=10)
        
    #     # Combine lines
    #     all_lines = cv2.add(horizontal_lines, vertical_lines)
        
    #     # NEW: Close gaps to form connected boundaries
    #     # Use a larger kernel to connect nearby line segments
    #     closing_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    #     all_lines = cv2.morphologyEx(all_lines, cv2.MORPH_CLOSE, closing_kernel, iterations=2)
        
    #     # Optional: Fill any remaining small holes
    #     # This ensures a solid closed contour
    #     closing_kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    #     all_lines = cv2.morphologyEx(all_lines, cv2.MORPH_CLOSE, closing_kernel2, iterations=1)
        
    #     return all_lines

    def remove_table_lines(self, inverted_image: cv2.typing.MatLike) -> None:
        """Improved line removal that preserves text better"""
        
        all_lines = self.extract_horizontal_and_vertical_lines(inverted_image)
        # Minimal dilation to ensure complete coverage
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        all_lines_dilated = cv2.dilate(all_lines, kernel, iterations=1)
        self.combined_lines = all_lines_dilated

        # Subtract combined lines from inverted image to get only table elements (without bounds)
        self.image_without_lines = cv2.subtract(inverted_image, all_lines_dilated)
        
        # No noise removal (or very minimal)
        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        # self.image_without_lines_noise_removed = cv2.morphologyEx(self.image_without_lines, cv2.MORPH_OPEN, kernel, iterations=1)
        # self.image_without_lines_noise_removed = self.image_without_lines
        self.image_without_lines = cv2.GaussianBlur(self.image_without_lines, (5,5), 0)
        # self.image_without_lines = cv2.GaussianBlur(self.image_without_lines, (3,3), 0)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        self.image_without_lines_noise_removed = cv2.dilate(self.image_without_lines, kernel, iterations=0)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        self.image_without_lines_noise_removed = cv2.erode(self.image_without_lines_noise_removed, kernel, iterations=0)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        self.image_without_lines_noise_removed = cv2.dilate(self.image_without_lines_noise_removed, kernel, iterations=0)