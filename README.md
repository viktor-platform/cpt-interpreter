![](https://img.shields.io/badge/SDK-v14.0.0-blue) <Please check version is the same as specified in requirements.txt>

# CPT interpretation
This sample app shows show how to interpret a CPT (.gef) to a soil layout using a classification method of choice.

The goal of this app is to demonstrate how the VIKTOR platform is used in the geotechnical engineering industry. This
app is a simplified version of a type of app used by geotechnical engineers to analyse the soil layout. Soil layout 
analyses are important for the construction industry, as many calculations rely on an accurate modelling of the soil. 
Soil layouts are used in processes such as:
- soil bearing capacity calculations
- pile drive predictions
- designing structures that interact with the soil, such as quay wall, sheet piles, etc.
- etc.

This app can consist of a single editor with steps to guide the user. The image below is an example of a result of a cpt file interpretation. 
On the left there is the input where the interpreted results can be adjusted manually. On the right the soil layer interpretation is shown with its data.

A published version of this app is available on [demo.viktor.ai](https://demo.viktor.ai/workspaces/63/app/).

![](resources/cpt_visualisation.png)

Here is an animation going through the steps: 
- Step 1: Uploading a .gef file
- Step 2: Choosing a classification method
- Step 3: Classifying the soil layout
- Step 4: Interpreting the results

![](resources/steps.gif)


## App structure
This is an editor-only app type.
