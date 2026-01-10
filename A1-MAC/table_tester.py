import cv2
from pathlib import Path
from table_content_extractor import TableExtractor

def main():
    tableExtractor = TableExtractor(Path() / "table_orig_test.png")
    preprocessed_image = tableExtractor.preprocess_image()
    # tableExtractor.show_image(ImageType.PREPROCESSED)
    tableExtractor.find_contours(preprocessed_image)
    tableExtractor.filter_contours_and_leave_only_rectangles()
    tableExtractor.find_largest_contour_by_area()
    # cv2.imwrite(Path() / "outputs/contours/contours.png", tableExtractor.image_with_contour_with_max_area)
    # cv2.waitKey(0)
    tableExtractor.order_points_in_the_contour_with_max_area()
    tableExtractor.calculate_new_width_and_height_of_image()
    tableExtractor.apply_perspective_transform()
    tableExtractor.add_10_percent_padding()
    cv2.imwrite(Path() / "outputs/contours/perspective.png", tableExtractor.perspective_corrected_image_with_padding)
    preprocessed_image = tableExtractor.preprocess_till_invert(tableExtractor.perspective_corrected_image_with_padding)
    tableExtractor.remove_table_lines(preprocessed_image)
    cv2.imwrite(Path() / "outputs/result/result.png", tableExtractor.image_without_lines_noise_removed)
    return

if __name__ == "__main__":
    main()