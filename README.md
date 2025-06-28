# dear_niece
This is a repository for predicting the marks for my beloved niece.


# Data

the data are obtained for:

- admission marks per university department
  - [2023](https://aeitei.gr/index.php?year=2023&pedio=3&likio_type=gh&order=2)
  - [2024](https://aeitei.gr/index.php?sist=&sys=&vasi=basi&year=2024&pedio=3&aeitei=&city=&likio_type=gh&cat=1&order=2)
- distibution of students marks per class and students:
  - [2022](https://foititikanea.gr/statistika/2022/pinakes/8.php)
  - [2023](https://www.aeitei.gr/statistika-gel.php?year=2023)
  - [2024](https://www.aeitei.gr/statistika-gel.php?year=2024)


# Methodology

## DOne:

I estimated that only the higher values will affect the process. 
As a result, and I calculated an (arbitrary metric to calculate the effect between years.


## Todo:

This was arbitrary and the next idea is to create a function that returns the percentile for each class per year, and estimate the shift of the 10%  (or other percentile for each year), for each of the classes and then calculate the expected 10% value for each distribution and its shift (assuming high correlation here)