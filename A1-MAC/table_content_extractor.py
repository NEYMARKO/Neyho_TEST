import cv2
import numpy as np
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
        self.original_image_with_all_contours = self.original_image.copy()
        cv2.drawContours(self.original_image_with_all_contours, self.contours, -1, (0, 255, 0), 3)
    
    def filter_contours_and_leave_only_rectangles(self):
        self.rectangular_contours = []
        for contour in self.contours:
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
        existing_image_width = self.original_image.shape[1]
        existing_image_width_reduced_by_10_percent = int(existing_image_width * 0.9)
        
        distance_between_top_left_and_top_right = self.calculateDistanceBetween2Points(self.contour_with_max_area_ordered[0], self.contour_with_max_area_ordered[1])
        distance_between_top_left_and_bottom_left = self.calculateDistanceBetween2Points(self.contour_with_max_area_ordered[0], self.contour_with_max_area_ordered[3])
        aspect_ratio = distance_between_top_left_and_bottom_left / distance_between_top_left_and_top_right
        self.new_image_width = existing_image_width_reduced_by_10_percent
        self.new_image_height = int(self.new_image_width * aspect_ratio)
    def apply_perspective_transform(self):
        pts1 = np.float32(self.contour_with_max_area_ordered)
        pts2 = np.float32([[0, 0], [self.new_image_width, 0], [self.new_image_width, self.new_image_height], [0, self.new_image_height]])
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        self.perspective_corrected_image = cv2.warpPerspective(self.original_image, matrix, (self.new_image_width, self.new_image_height))
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