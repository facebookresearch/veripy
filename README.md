//###################################################################################
//   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
//   The following information is considered proprietary and confidential to Facebook,
//   and may not be disclosed to any third party nor be used for any purpose other
//   than to full fill service obligations to Facebook
//###################################################################################
<!-- ABOUT THE PROJECT -->
## About The Project

Veripy is a python based parser that addresses the asic designer pain points 
for asic development.

veripy_build.py is a python based build script to automate bottom-up build   
of veripy at a block level. The user needs to parse the top psv file name as 
input along with other run command options for veripy. It gathers all the    
dependencies for every module in a hierarchical fashion and generates the    
bottom buid flow for veripy. 

### TL;DR






<!-- GETTING STARTED -->
## Getting Started

Setup the environment variable ROOT

export ROOT=<path_to_veripy_directory>

cd demo/pyramid_gen_0/src

make makeinc

make build



<!-- USAGE EXAMPLES -->
## Usage

### General APIs




<!-- FOR DEVELOPERS -->

<!-- CONTACT -->
## Contact

Baheerathan Anandharengan - baheerathan@meta.com

Dheepak Jayaraman - dheepak@meta.com


## Copyright

Copyright (c) Meta Platforms, Inc. and affiliates.

All licenses in this repository are copyrighted by their respective authors.
Everything else is released under CC0. See `LICENSE` for details.
