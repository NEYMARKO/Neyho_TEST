import cv2
import numpy as np
from pathlib import Path

    
class TableExtractor:
    def __init__(self, image_path : Path, file_basename):
        self.original_image = cv2.imread(str(image_path))
        # height, width, channels = self.original_image.shape
        # self.original_image = self.original_image[0:int(0.5 * height), 0:width]
        self.file_basename = file_basename
        self.root_output_folder = Path() / "outputs"
        self.preprocessed_output_folder = self.root_output_folder / "preprocessed"

    def extract_table_with_fixed_perspective(self, save_path : Path) -> None:
        if not save_path.parent.exists() or not save_path.parent.is_dir():
            save_path.parent.mkdir(parents=True, exist_ok=True)
        preprocessed_image = self.preprocess_image()
        # tableExtractor.show_image(ImageType.PREPROCESSED)
        self.find_contours(preprocessed_image)
        cv2.imwrite(str(save_path.parent / "preprocessed.png"), preprocessed_image)
        self.filter_contours_and_leave_only_rectangles()
        self.find_largest_contour_by_area()
        # cv2.imwrite(Path() / "outputs/contours/contours.png", tableExtractor.image_with_contour_with_max_area)
        # cv2.waitKey(0)
        self.order_points_in_the_contour_with_max_area()
        self.calculate_new_width_and_height_of_image()
        self.apply_perspective_transform()
        # self.add_10_percent_padding()
        # preprocessed_image = self.preprocess_till_invert(self.perspective_corrected_image_with_padding)
        preprocessed_image = self.preprocess_till_invert(self.perspective_corrected_image)
        # cv2.imwrite(str(save_path.parent / "correct_perspective_with_padding.png"), self.perspective_corrected_image_with_padding)
        # cv2.imwrite(str(save_path.parent / "all_contours.png"), self.original_image_with_all_contours)
        cv2.imwrite(str(save_path.parent / "perspective.png"), self.perspective_corrected_image)
        cv2.imwrite(str(save_path.parent / "rectangular_contours.png"), self.original_image_with_only_rectangular_contours)
        cv2.imwrite(str(save_path.parent / "contour_with_max_area.png"), self.original_image_with_contour_with_max_area)
        return 
    
    def clear_table(self, save_path : Path) -> None:
        self.extract_table_with_fixed_perspective(save_path)
        # preprocessed_image = self.preprocess_till_invert(self.perspective_corrected_image_with_padding)
        preprocessed_image = self.preprocess_till_invert(self.perspective_corrected_image)
        self.remove_table_lines(preprocessed_image)
        cv2.imwrite(str(save_path.parent / "combined_lines.png"), self.combined_lines)
        cv2.imwrite(str(save_path), self.image_without_lines_noise_removed)
        return

    def preprocess_image(self, input_image : cv2.typing.MatLike | None = None) -> cv2.typing.MatLike:
        if not input_image:
            input_image = self.original_image
        inverted_img = self.preprocess_till_invert(input_image)
        dilated_img = cv2.dilate(inverted_img, None, iterations=5)
        return dilated_img
    
    def preprocess_till_invert(self, input_image : cv2.typing.MatLike | None = None) -> cv2.typing.MatLike:
        gray_img = cv2.cvtColor(self.original_image if input_image is None else input_image, cv2.COLOR_BGR2GRAY)
        threshold_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        inverted_img = cv2.bitwise_not(threshold_img)
        return inverted_img
    def find_contours(self, image : cv2.typing.MatLike) -> None:
        self.contours, self.hierarchy = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.original_image_with_all_contours = self.original_image.copy()
        cv2.drawContours(self.original_image_with_all_contours, self.contours, -1, (0, 255, 0), 3)
    
    def filter_contours_and_leave_only_rectangles(self):
        self.rectangular_contours = []
        for contour in self.contours:
            # rect = cv2.minAreaRect(contour)
            # rect = cv2.boundingRect(contour)
            # box = cv2.boxPoints(rect)
            # box = np.intp(box)
            # self.rectangular_contours.append(box)
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                self.rectangular_contours.append(approx)
        # Below lines are added to show all rectangular contours
        # This is not needed, but it is useful for debugging
        self.original_image_with_only_rectangular_contours = self.original_image.copy()
        cv2.drawContours(self.original_image_with_only_rectangular_contours, self.rectangular_contours, -1, (0, 255, 0), 3)

    def find_largest_contour_by_area(self):
        max_area = 0
        self.contour_with_max_area = None
        for contour in self.rectangular_contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                max_area = area
                self.contour_with_max_area = contour
        # Below lines are added to show the contour with max area
        # This is not needed, but it is useful for debugging
        self.original_image_with_contour_with_max_area = self.original_image.copy()
        cv2.drawContours(self.original_image_with_contour_with_max_area, [self.contour_with_max_area], -1, (0, 255, 0), 3)

    def find_and_filter_contours(self) -> None:
        """
        1. Uses OpenCV to find all contours.
        2. Loops through the countours and leaves only the rectangular ones.
        3. Finds the largest contour by area - is presumed to be the table.
        """
        return

    def add_10_percent_padding(self):
        image_height = self.original_image.shape[0]
        padding = int(image_height * 0.1)
        self.perspective_corrected_image_with_padding = cv2.copyMakeBorder(self.perspective_corrected_image, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=[255, 255, 255])

    def order_points_in_the_contour_with_max_area(self):
        self.contour_with_max_area_ordered = self.order_points(self.contour_with_max_area)
        # The code below is to plot the points on the image
        # it is not required for the perspective transform
        # it will help you to understand and debug the code
        self.original_image_with_points_plotted = self.original_image.copy()
        for point in self.contour_with_max_area_ordered:
            point_coordinates = (int(point[0]), int(point[1]))
            self.original_image_with_points_plotted = cv2.circle(self.original_image_with_points_plotted, point_coordinates, 10, (0, 0, 255), -1)
    def calculate_new_width_and_height_of_image(self):
        top_left, top_right, bottom_right, bottom_left = self.contour_with_max_area_ordered

        width_top = np.linalg.norm(top_right - top_left)
        width_bottom = np.linalg.norm(bottom_right - bottom_left)
        height_left = np.linalg.norm(bottom_left - top_left)
        height_right = np.linalg.norm(bottom_right - top_right)

        target_width = int(max(width_top, width_bottom))
        target_height = int(max(height_left, height_right))

        # existing_image_width = self.original_image.shape[1]
        # existing_image_width_reduced_by_10_percent = int(existing_image_width * 0.9)
        
        # distance_between_top_left_and_top_right = self.calculateDistanceBetween2Points(self.contour_with_max_area_ordered[0], self.contour_with_max_area_ordered[1])
        # distance_between_top_left_and_bottom_left = self.calculateDistanceBetween2Points(self.contour_with_max_area_ordered[0], self.contour_with_max_area_ordered[3])
        # aspect_ratio = distance_between_top_left_and_bottom_left / distance_between_top_left_and_top_right
        # self.new_image_width = existing_image_width_reduced_by_10_percent
        # self.new_image_height = int(self.new_image_width * aspect_ratio)
        self.new_image_width = target_width
        self.new_image_height = target_height
    def apply_perspective_transform(self):
        pts1 = np.float32(self.contour_with_max_area_ordered)
        pts2 = np.float32([
            [0, 0], 
            [self.new_image_width - 1, 0], 
            [self.new_image_width - 1, self.new_image_height - 1], 
            [0, self.new_image_height - 1]]
        )
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        self.perspective_corrected_image = cv2.warpPerspective(
            self.original_image, 
            matrix, 
            (self.new_image_width, self.new_image_height), 
            flags=cv2.INTER_CUBIC,  # ✅ Better for text
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        kernel_sharpen = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])
        self.perspective_corrected_image = cv2.filter2D(self.perspective_corrected_image, -1, kernel_sharpen)
    # Below are helper functions
    def calculateDistanceBetween2Points(self, p1, p2):
        dis = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        return dis
    def order_points(self, pts):
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


    def erode_vertical_lines(self, inverted_image : cv2.typing.MatLike) -> None:
        hor = np.array([[1,1,1,1,1,1]])
        self.vertical_lines_eroded_image = cv2.erode(inverted_image, hor, iterations=5)
        self.vertical_lines_eroded_image = cv2.dilate(self.vertical_lines_eroded_image, hor, iterations=10)
        return
    def erode_horizontal_lines(self, inverted_image : cv2.typing.MatLike) -> None:
        ver = np.array([[1],
            [1],
            [1],
            [1],
            [1],
            [1],
            [1]])
        self.horizontal_lines_eroded_image = cv2.erode(inverted_image, ver, iterations=5)
        self.horizontal_lines_eroded_image = cv2.dilate(self.horizontal_lines_eroded_image, ver, iterations=10)
        return
    def combine_erroded_images(self) -> None:
        self.combined_image = cv2.add(self.vertical_lines_eroded_image, self.horizontal_lines_eroded_image)
        return
    

    def dilate_combined_image_to_make_lines_thicker(self) -> None:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.combined_image_dilated = cv2.dilate(self.combined_image, kernel, iterations=1)
        return

    def subtract_combined_and_dilated_image_from_original_image(self, inverted_image : cv2.typing.MatLike) -> None:
        self.image_without_lines = cv2.subtract(inverted_image, self.combined_image_dilated)
        return
    
    def remove_noise_with_erode_and_dilate(self) -> None:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        self.image_without_lines_noise_removed = cv2.erode(self.image_without_lines, kernel, iterations=0)
        self.image_without_lines_noise_removed = cv2.dilate(self.image_without_lines_noise_removed, kernel, iterations=0)
        return
    

    def remove_table_lines(self, inverted_image: cv2.typing.MatLike) -> None:
        """Improved line removal that preserves text better"""
        
        # Use longer kernels to detect only long lines (not text strokes)
        # Horizontal lines (at least 40-50 pixels long)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 1))
        horizontal_lines = cv2.erode(inverted_image, horizontal_kernel, iterations=5)
        horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=10)
        # horizontal_lines = cv2.morphologyEx(inverted_image, cv2.MORPH_OPEN, horizontal_kernel, iterations=10)
        
        # Vertical lines (at least 40-50 pixels long)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 10))
        vertical_lines = cv2.erode(inverted_image, vertical_kernel, iterations=5)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=10)
        # vertical_lines = cv2.morphologyEx(inverted_image, cv2.MORPH_OPEN, vertical_kernel, iterations=10)
        
        # Combine
        all_lines = cv2.add(horizontal_lines, vertical_lines)
        
        # Minimal dilation to ensure complete coverage
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        all_lines_dilated = cv2.dilate(all_lines, kernel, iterations=1)
        self.combined_lines = all_lines_dilated

        # Subtract
        self.image_without_lines = cv2.subtract(inverted_image, all_lines_dilated)
        
        # No noise removal (or very minimal)
        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        # self.image_without_lines_noise_removed = cv2.morphologyEx(self.image_without_lines, cv2.MORPH_OPEN, kernel, iterations=1)
        # self.image_without_lines_noise_removed = self.image_without_lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.image_without_lines_noise_removed = cv2.dilate(self.image_without_lines, kernel, iterations=3)
        self.image_without_lines_noise_removed = cv2.erode(self.image_without_lines, kernel, iterations=1)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        self.image_without_lines_noise_removed = cv2.dilate(self.image_without_lines, kernel, iterations=1)
    # def remove_table_lines(self, inverted_image : cv2.typing.MatLike) -> None:
    #     self.erode_horizontal_lines(inverted_image)
    #     self.erode_vertical_lines(inverted_image)
    #     cv2.imwrite(Path() / "outputs/result/new_horizontal_erroded.png", self.horizontal_lines_eroded_image)
    #     cv2.imwrite(Path() / "outputs/result/vertical_erroded.png", self.vertical_lines_eroded_image)
    #     self.combine_erroded_images()
    #     self.dilate_combined_image_to_make_lines_thicker()
    #     cv2.imwrite(Path() / "outputs/result/combined_eroded.png", self.combined_image_dilated)
    #     self.subtract_combined_and_dilated_image_from_original_image(inverted_image)
    #     self.remove_noise_with_erode_and_dilate()