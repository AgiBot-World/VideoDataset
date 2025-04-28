import torchvision.transforms as transforms


class RuntimeImageResize:
    def __init__(self, size=(224, 224)):
        # image shape: [C,H,W]
        self.size = size

    def __call__(self, sample):
        images = sample["images"]
        new_images = []
        for image in images:
            img = image.resize(self.size)
            new_images.append(img)
        sample["images"] = new_images
        return sample


runtime_transform = transform = transforms.Compose(
    [
        RuntimeImageResize(size=(448, 448)),
    ]
)
