# Common Components for Langflow

This repository contains a collection of custom components designed for use with [Langflow](https://github.com/langflow-ai/langflow).

<img width="1506" height="734" alt="screen" src="https://github.com/user-attachments/assets/57e9d714-0338-4c16-a226-58926062fc91" />

## Installation

To use these components in your Langflow setup, add the following environment variable to your Langflow configuration:

```bash
LANGFLOW_BUNDLE_URLS="https://github.com/iann0036/langflow-common-components"
```

If you want to use the AWS re:Invent Session Search component without manually supplying `rfapiprofileid` and `rfwidgetid`, also install Playwright and its Chromium browser:

```bash
pip install playwright
playwright install chromium
```
