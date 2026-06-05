<img src="../imgs/header_bar.png" alt="OmniTool Header" width="100%">

# OmniTool

Control a Windows 11 VM with OmniParser + your vision model of choice.

## Highlights:

1. **OmniParser V2** is 60% faster than V1 and now understands a wide variety of OS, app and inside app icons!
2. **HostControl** runs on the current desktop session and provides the computer use API via localhost
3. **OmniTool** supports out of the box the following vision models - OpenAI (4o/o1/o3-mini), DeepSeek (R1), Qwen (2.5VL) or Anthropic Computer Use

## Overview

There are two components:

<table style="border-collapse: collapse; border: none;">
  <tr>
    <td style="border: none;"><img src="../imgs/omniparsericon.png" width="50"></td>
    <td style="border: none;"><strong>omniparserserver</strong></td>
    <td style="border: none;">FastAPI server running OmniParser V2.</td>
  </tr>
  <tr>
    <td style="border: none;"><img src="../imgs/gradioicon.png" width="50"></td>
    <td style="border: none;"><strong>gradio</strong></td>
    <td style="border: none;">UI to provide commands and watch reasoning + execution on the current desktop session</td>
  </tr>
</table>

## Showcase Video
| OmniParser V2 | [Watch Video](https://1drv.ms/v/c/650b027c18d5a573/EWXbVESKWo9Buu6OYCwg06wBeoM97C6EOTG6RjvWLEN1Qg?e=alnHGC) |
|--------------|------------------------------------------------------------------|
| OmniTool    | [Watch Video](https://1drv.ms/v/c/650b027c18d5a573/EehZ7RzY69ZHn-MeQHrnnR4BCj3by-cLLpUVlxMjF4O65Q?e=8LxMgX) |


## Notes:

1. Though **OmniParser V2** can run on a CPU, we have separated this out if you want to run it fast on a GPU machine
2. The desktop control server can run directly on your current Windows desktop session.
3. The Gradio UI can run on a CPU machine while **omniparserserver** runs on a GPU server.

## Setup

1. **omniparserserver**:

   a. If you already have a conda environment for OmniParser, you can use that. Else follow the following steps to create one

   b. Ensure conda is installed with `conda --version` or install from the [Anaconda website](https://www.anaconda.com/download/success)

   c. Navigate to the root of the repo with `cd OmniParser`

   d. Create a conda python environment with `conda create -n "omni" python==3.12`

   e. Set the python environment to be used with `conda activate omni`

   f. Install the dependencies with `pip install -r requirements.txt`

   g. Continue from here if you already had the conda environment.

   h. Ensure you have the V2 weights downloaded in weights folder (**ensure caption weights folder is called icon_caption_florence**). If not download them with:
   ```
   rm -rf weights/icon_detect weights/icon_caption weights/icon_caption_florence 
   for folder in icon_caption icon_detect; do huggingface-cli download microsoft/OmniParser-v2.0 --local-dir weights --repo-type model --include "$folder/*"; done
   mv weights/icon_caption weights/icon_caption_florence
   ```

   h. Navigate to the server directory with `cd OmniParser/omnitool/omniparserserver`

   i. Start the server with `python -m omniparserserver`

2. **desktop control server**:

  a. Navigate to `cd OmniParser/omnitool/hostcontrol`

  b. Start the server with `python main.py --host 127.0.0.1 --port 5000 --allow_unsafe_execute`

  c. Validate the server is up with `curl http://127.0.0.1:5000/probe`

3. **gradio**:

   a. Navigate to the gradio directory with `cd OmniParser/omnitool/gradio`

   b. Ensure you have activated the conda python environment with `conda activate omni`

  c. Start the server with `python app.py --omniparser_server_url localhost:8000`

   d. Open the URL in the terminal output, set your API Key and start playing with the AI agent!

## Common setup errors
### Validation errors: Windows Host is not responding
If you get this error in Gradio after clicking submit, the desktop control server is unavailable. Check with `curl http://127.0.0.1:5000/probe` and make sure you started `python main.py --host 127.0.0.1 --port 5000 --allow_unsafe_execute` from `omnitool/hostcontrol`.

### libpaddle: The specified module could not be found
The OCR library used by OmniParser is Paddle that depends on C++ Redistributable on Windows. If you are on Windows ensure that you have installed it, then rerun installing the requirements.txt. More details [here](https://github.com/microsoft/OmniParser/issues/140#issuecomment-2670619168).

## Risks and Mitigations
To align with the Microsoft AI principles and Responsible AI practices, we conduct risk mitigation by training the icon caption model with Responsible AI data, which helps the model avoid inferring sensitive attributes (e.g.race, religion etc.) of the individuals which happen to be in icon images as much as possible. At the same time, we encourage user to apply OmniParser only for screenshot that does not contain harmful/violent content. For the OmniTool, we conduct threat model analysis using Microsoft Threat Modeling Tool. We advise human to stay in the loop in order to minimize risk.


## Acknowledgment 
Kudos to the amazing resources that are invaluable in the development of our code: [Claude Computer Use](https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/README.md), [OS World](https://github.com/xlang-ai/OSWorld), [Windows Agent Arena](https://github.com/microsoft/WindowsAgentArena), and [computer_use_ootb](https://github.com/showlab/computer_use_ootb).
We are grateful for helpful suggestions and feedbacks provided by Francesco Bonacci, Jianwei Yang, Dillon DuPont, Yue Wu, Anh Nguyen.
Many thanks to @keyserjaya for early setup feedback.
