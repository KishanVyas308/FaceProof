"""Creates a sample test image for fixtures."""

from PIL import Image, ImageDraw


def create_sample_face(output_path: str = "tests/fixtures/sample_test_image.jpg"):
    # Create simple graphic image with dimensions 400x400
    img = Image.new("RGB", (400, 400), color=(240, 240, 245))
    draw = ImageDraw.Draw(img)

    # Face circle
    draw.ellipse([100, 80, 300, 320], fill=(255, 220, 180), outline=(200, 160, 120), width=3)
    # Eyes
    draw.ellipse([150, 150, 180, 180], fill=(50, 50, 80))
    draw.ellipse([220, 150, 250, 180], fill=(50, 50, 80))
    # Nose
    draw.line([200, 190, 195, 230], fill=(180, 130, 90), width=3)
    draw.line([195, 230, 210, 230], fill=(180, 130, 90), width=3)
    # Mouth
    draw.arc([160, 240, 240, 270], start=0, end=180, fill=(180, 60, 60), width=3)

    img.save(output_path, "JPEG", quality=95)
    print(f"Sample test image saved to {output_path}")


if __name__ == "__main__":
    create_sample_face()
