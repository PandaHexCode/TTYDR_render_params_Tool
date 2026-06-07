# TTYDR_render_params_Tool
The tool is currently in the testing phase and is not yet fully developed.

# How to use it
First you need to have pyhton installed, and then you need to run that command <br>
`pip install zstandard`<br> 
Then you need the hash_strings.txt file from [Light Converter from KillzXGaming (That tool crashes the game)](https://github.com/KillzXGaming/Paper-Mario-Tools/releases/tag/v1.2) , place it in the same folder as the .py and the .data
after that place the .py in the same folder as the .render_params.data file, <br> 
Then run this command to extract a file <br> 
`python cam_tool.py extract "D:\YOUR_PATH\render_params.data"`<br> 
and then to pack it use<br> 
`python cam_tool.py pack "D:\YOUR_PATH\render_params.data.json"`<br> 
the render_params.data must be in the same folder as the json.
