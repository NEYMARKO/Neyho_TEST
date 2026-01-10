import cv2
from enum import Enum
from pathlib import Path

class ImageType(Enum):
    ORIGINAL = 1
    PREPROCESSED = 2
class TableExtractor:
    def __init__(self, image_path : Path):
        self.original_image = cv2.imread(image_path.name)
        self.preprocessed_image = None
        self.root_output_folder = Path() / "outputs"
        self.preprocessed_output_folder = self.root_output_folder / "preprocessed"

    def preprocess_image(self) -> None:
        gray_img = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        threshold_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        inverted_img = cv2.bitwise_not(threshold_img)
        dilated_img = cv2.dilate(inverted_img, None, iterations=5)
        self.preprocessed_image = dilated_img
        cv2.imwrite(f"{self.preprocessed_output_folder}/preprocessed.png", self.preprocessed_image)
        return
    
    def find_contours(self) -> None:
        self.contours, self.hierarchy = cv2.findContours(self.preprocessed_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        self.image_with_all_contours = self.original_image.copy()
        cv2.drawContours(self.image_with_all_contours, self.contours, -1, (0, 255, 0), 3)
    
    def filter_contours_and_leave_only_rectangles(self):
        self.rectangular_contours = []
        for contour in self.contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                self.rectangular_contours.append(approx)
        # Below lines are added to show all rectangular contours
        # This is not needed, but it is useful for debugging
        self.image_with_only_rectangular_contours = self.original_image.copy()
        cv2.drawContours(self.image_with_only_rectangular_contours, self.rectangular_contours, -1, (0, 255, 0), 3)

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
        self.image_with_contour_with_max_area = self.original_image.copy()
        cv2.drawContours(self.image_with_contour_with_max_area, [self.contour_with_max_area], -1, (0, 255, 0), 3)

    def find_and_filter_contours(self) -> None:
        """
        1. Uses OpenCV to find all contours.
        2. Loops through the countours and leaves only the rectangular ones.
        3. Finds the largest contour by area - is presumed to be the table.
        """
        return

    def show_image(self, type : ImageType) -> None:
        match type:
            case ImageType.ORIGINAL:
                cv2.imshow('original_image', self.original_image)
                return
            case ImageType.PREPROCESSED:
                cv2.imshow('preprocessed_image', self.preprocessed_image)
            case _:
                return
        cv2.waitKey(0)
        return