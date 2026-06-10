# OmniParser: Screen Parsing tool for Pure Vision Based GUI Agent

<p align="center">
  <img src="imgs/logo.png" alt="Logo">
</p>
<!-- <a href="https://trendshift.io/repositories/12975" target="_blank"><img src="https://trendshift.io/api/badge/repositories/12975" alt="microsoft%2FOmniParser | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a> -->

[![arXiv](https://img.shields.io/badge/Paper-green)](https://arxiv.org/abs/2408.00203)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

📢 [[Project Page](https://microsoft.github.io/OmniParser/)] [[V2 Blog Post](https://www.microsoft.com/en-us/research/articles/omniparser-v2-turning-any-llm-into-a-computer-use-agent/)] [[Models V2](https://huggingface.co/microsoft/OmniParser-v2.0)] [[Models V1.5](https://huggingface.co/microsoft/OmniParser)] [[HuggingFace Space Demo](https://huggingface.co/spaces/microsoft/OmniParser-v2)]

**OmniParser** is a comprehensive method for parsing user interface screenshots into structured and easy-to-understand elements, which significantly enhances the ability of GPT-4V to generate actions that can be accurately grounded in the corresponding regions of the interface. 

## News
- [2025/3] We support local logging of trajecotry so that you can use OmniParser+OmniTool to build training data pipeline for your favorate agent in your domain. [Documentation WIP]
- [2025/3] We are gradually adding multi agents orchstration and improving user interface in OmniTool for better experience.
- [2025/2] We release OmniParser V2 [checkpoints](https://huggingface.co/microsoft/OmniParser-v2.0). [Watch Video](https://1drv.ms/v/c/650b027c18d5a573/EWXbVESKWo9Buu6OYCwg06wBeoM97C6EOTG6RjvWLEN1Qg?e=alnHGC)
- [2025/2] We introduce OmniTool: Control a Windows 11 VM with OmniParser + your vision model of choice. OmniTool supports out of the box the following large language models - OpenAI (4o/o1/o3-mini), DeepSeek (R1), Qwen (2.5VL) or Anthropic Computer Use. [Watch Video](https://1drv.ms/v/c/650b027c18d5a573/EehZ7RzY69ZHn-MeQHrnnR4BCj3by-cLLpUVlxMjF4O65Q?e=8LxMgX)
- [2025/1] V2 is coming. We achieve new state of the art results 39.5% on the new grounding benchmark [Screen Spot Pro](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding/tree/main) with OmniParser v2 (will be released soon)! Read more details [here](https://github.com/microsoft/OmniParser/tree/master/docs/Evaluation.md).
- [2024/11] We release an updated version, OmniParser V1.5 which features 1) more fine grained/small icon detection, 2) prediction of whether each screen element is interactable or not. Examples in the demo.ipynb. 
- [2024/10] OmniParser was the #1 trending model on huggingface model hub (starting 10/29/2024). 
- [2024/10] Feel free to checkout our demo on [huggingface space](https://huggingface.co/spaces/microsoft/OmniParser)! (stay tuned for OmniParser + Claude Computer Use)
- [2024/10] Both Interactive Region Detection Model and Icon functional description model are released! [Hugginface models](https://huggingface.co/microsoft/OmniParser)
- [2024/09] OmniParser achieves the best performance on [Windows Agent Arena](https://microsoft.github.io/WindowsAgentArena/)! 

## Install 
First clone the repo, and then install environment:
```python
cd OmniParser
conda create -n "omni" python==3.12
conda activate omni
pip install -r requirements.txt
```

Ensure you have the V2 weights downloaded in weights folder (ensure caption weights folder is called icon_caption_florence). If not download them with:
```
   # download the model checkpoints to local directory OmniParser/weights/
   for f in icon_detect/{train_args.yaml,model.pt,model.yaml} icon_caption/{config.json,generation_config.json,model.safetensors}; do huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights; done
   mv weights/icon_caption weights/icon_caption_florence
```

<!-- ## [deprecated]
Then download the model ckpts files in: https://huggingface.co/microsoft/OmniParser, and put them under weights/, default folder structure is: weights/icon_detect, weights/icon_caption_florence, weights/icon_caption_blip2. 

For v1: 
convert the safetensor to .pt file. 
```python
python weights/convert_safetensor_to_pt.py

For v1.5: 
download 'model_v1_5.pt' from https://huggingface.co/microsoft/OmniParser/tree/main/icon_detect_v1_5, make a new dir: weights/icon_detect_v1_5, and put it inside the folder. No weight conversion is needed. 
``` -->

## Examples:
We put together a few simple examples in the demo.ipynb. 

## Gradio Demo
To run gradio demo, simply run:
```python
python gradio_demo.py
```

## Local Apple Silicon Run

On Apple Silicon Macs, you can run the parser natively with PyTorch MPS instead of Docker. This is the practical local GPU path on macOS.

### One-time setup

Create a Python 3.11 virtual environment and install the parser-serving dependencies:

```bash
/opt/homebrew/bin/python3.11 -m venv .venv311
.venv311/bin/pip install --upgrade pip setuptools wheel
.venv311/bin/pip install -r requirements-runpod.txt
```

Populate the local `weights/` directory. If you already built the Docker image from this repo, you can reuse the baked weights instead of downloading them again:

```bash
cid=$(docker create omniparser-runpod:test)
rm -rf weights
mkdir -p weights
docker cp "$cid":/app/weights/. ./weights
docker rm "$cid"
```

If you do not have the Docker image locally, download the weights from Hugging Face as described in the install section above.

### Start the local MPS server

Use the helper script:

```bash
./scripts/run-local-mps.sh
```

Or run the server directly:

```bash
PYTHONUNBUFFERED=1 OMNIPARSER_DEVICE=mps OMNIPARSER_PORT=8001 OMNIPARSER_PRELOAD=false .venv311/bin/python omnitool/omniparserserver/omniparserserver.py --host 127.0.0.1 --port 8001 --device mps
```

### Validate locally

```bash
curl -sS http://127.0.0.1:8001/probe/

image_base64=$(base64 < imgs/logo.png | tr -d '\n')
curl -sS -X POST http://127.0.0.1:8001/parse/ \
  -H 'Content-Type: application/json' \
  --data "{\"base64_image\":\"$image_base64\"}"
```

Notes:

- `OMNIPARSER_PRELOAD=false` gets the API up immediately and shifts model initialization to the first parse request.
- The native MPS path was validated on an Apple M1 Pro with `OMNIPARSER_DEVICE=mps`.
- Docker Desktop on macOS does not expose the Apple GPU to Linux containers, so this native path is the local GPU option.

## Runpod Deployment

The repo now includes a dual-mode Runpod entrypoint so you can iterate on a GPU pod over SSH and later promote the same image to a Serverless endpoint.

### Build the image

Use the parser-focused dependencies and bake the OmniParser v2 weights into the image during the build:

```bash
docker build --platform linux/amd64 -t YOUR_DOCKERHUB_USER/omniparser-runpod:latest .
docker push YOUR_DOCKERHUB_USER/omniparser-runpod:latest
```

### Pod-first iteration

1. Deploy the image to a Runpod Pod.
2. Set `MODE_TO_RUN=pod`.
3. Optionally set `PUBLIC_KEY` to enable SSH inside the container.
4. The container starts the FastAPI service from `omnitool/omniparserserver/omniparserserver.py` on port `8000`.
5. Test readiness with `curl http://127.0.0.1:8000/probe/`.

### Serverless promotion

1. Create a Serverless endpoint from the same image.
2. Set `MODE_TO_RUN=serverless`.
3. Send an event shaped like:

```json
{
  "input": {
    "base64_image": "..."
  }
}
```

The serverless handler returns the same parsing payload as the HTTP API: `som_image_base64`, `parsed_content_list`, and `latency`.

### Runtime configuration

The service accepts environment variables for the parser runtime:

- `OMNIPARSER_SOM_MODEL_PATH`
- `OMNIPARSER_CAPTION_MODEL_NAME`
- `OMNIPARSER_CAPTION_MODEL_PATH`
- `OMNIPARSER_DEVICE`
- `OMNIPARSER_BOX_THRESHOLD`
- `OMNIPARSER_HOST`
- `OMNIPARSER_PORT`
- `OMNIPARSER_PRELOAD`

## Model Weights License
For the model checkpoints on huggingface model hub, please note that icon_detect model is under AGPL license since it is a license inherited from the original yolo model. And icon_caption_blip2 & icon_caption_florence is under MIT license. Please refer to the LICENSE file in the folder of each model: https://huggingface.co/microsoft/OmniParser.

## 📚 Citation
Our technical report can be found [here](https://arxiv.org/abs/2408.00203).
If you find our work useful, please consider citing our work:
```
@misc{lu2024omniparserpurevisionbased,
      title={OmniParser for Pure Vision Based GUI Agent}, 
      author={Yadong Lu and Jianwei Yang and Yelong Shen and Ahmed Awadallah},
      year={2024},
      eprint={2408.00203},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2408.00203}, 
}
```
