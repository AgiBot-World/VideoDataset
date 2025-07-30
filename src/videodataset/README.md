## Converting AgiBot World to LeRobot format and using it with our LeRobotVideoDataset

1. **Download a sample of AgiBot World**
   The full [AgiBotWorld‑Alpha](https://huggingface.co/datasets/agibot-world/AgiBotWorld-Alpha) and [AgiBotWorld‑Beta](https://huggingface.co/datasets/agibot-world/AgiBotWorld-Beta) releases are very large. For experimentation, use the sample version of AgiBotWorld‑Alpha (\~7 GB) published by the authors. Download [sample_dataset.tar](https://huggingface.co/datasets/agibot-world/AgiBotWorld-Alpha/blob/main/sample_dataset.tar) from the Hugging Face dataset page.
   ```bash
   wget https://huggingface.co/datasets/agibot-world/AgiBotWorld-Alpha/blob/main/sample_dataset.tar
   tar -xf sample_dataset.tar
   ```

2. **Convert to LeRobot format**
   AgiBot World’s structure differs from the LeRobot dataset format, so it must be converted before use. Clone the [`any4lerobot`](https://github.com/Tavish9/any4lerobot) repository and follow the instructions in the `agibot2lerobot` directory. The conversion script requires the path to your downloaded AgiBot World data and an output directory. For example:

   ```bash
   git clone https://github.com/Tavish9/any4lerobot.git
   cd any4lerobot/agibot2lerobot
   python convert.py \
     --src-path /path/to/AgiBotWorld-Dataset \
     --output-path /path/to/converted_agibot \
     --eef-type gripper \
     --num-cpus-per-task 3
   ```

   See the [README.md](https://github.com/Tavish9/any4lerobot/blob/main/agibot2lerobot/README.md) for details on multi‑node usage.

3. **Load the converted dataset with the real‑time decoder**
   Once converted, the dataset can be loaded by `LeRobotVideoDataset` for GPU‑accelerated video decoding:

   ```python
   from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset

   vt_dataset = LeRobotVideoDataset(
       root="/path/to/converted_agibot",
   )
   ```

   This will enable real‑time GPU-side decoding of the converted AgiBot World videos within your deep‑learning workflows.


## General Video Decoder Usage

Below is the quickest way to plug the Zero-copy GPU decoder directly into your `torch.utils.data.Dataset`.


```python
import torch
from torch.utils.data import Dataset

from videodataset.dataset import BaseVideoDataset

SAMPLE_PATH = "/mnt/public/qiuying/output.mp4"

class DemoVideoDataset(Dataset, BaseVideoDataset): # BaseVideoDataset provides the basic decoder lifecycle management and decoding apis
    """Yields individual decoded frames from a single video."""


    def __init__(self, video_path: str):
        BaseVideoDataset.__init__(self)
        self.video_path = video_path

    def __getitem__(self, idx):
        # Decode a single frame in real-time on the GPU
        decoder = self.get_decoder(decoder_key=str(self.video_path), codec="h265")
        return self.decode_video_frame(
            decoder=decoder,
            video_path=self.video_path,
            frame_idx=idx
        )

# Instantiate the dataset
frames_ds = DemoVideoDataset(SAMPLE_PATH)
print(frames_ds[0].shape)   # e.g. torch.Size([3, 480, 640]) after RGB conversion
print(frames_ds[0].device)  # cuda:0
```
