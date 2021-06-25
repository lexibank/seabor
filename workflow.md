# Reproducing the study

1. Install dependencies:
   ```shell
   pip install -e .
   ```
   Please follow specific installation instructions for [cartopy](https://scitools.org.uk/cartopy/docs/latest/) and [igraph](https://igraph.org), since both packages will require non-Python packages to be installed on your system.
2. Optionally fetch raw data from EDICTOR:
   ```shell
   $ cldfbench download lexibank_seabor.py
   INFO    running _cmd_download on borrowing-detection-study ...
   ID             Source                        Varieties    Concepts
   -------------  --------------------------  -----------  ----------
   beidasinitic   Běijīng Dàxué (1964)                  6         146
   beidazihui     Běijīng Dàxué (1962)                  4         171
   castrosui      Castro and Pan (2015)                 3         211
   castroyi       Castro et al. (2010)                  1         222
   castrozhuang   Castro and Hansen (2010)              8         243
   chenhmongmien  Chén (2012)                          23         250
   housinitic     Hóu (2004)                           10          61
   houzihui       Hóu (2004)                            9          77
   liusinitic     Liú Lìlǐ 刘俐李 et al. (2007)            5         130
   wangbai        Wang (2004)                           1         144
   INFO    ... done borrowing-detection-study [1.0 secs]
   ```
3. Create the CLDF dataset augmented with automatically inferred attributes:
   ```shell
   $ cldfbench lexibank.makecldf lexibank_seabor.py
   ...
   method                           precision    recall    f-score
   -----------------------------  -----------  --------  ---------
   automated cognate detection         0.8710    0.8861     0.8785
   automated borrowing detection       0.9088    0.8439     0.8751
   ...
   ```
   This will take a couple of minutes. Results can slightly vary due ot the permutation procedure.

   In order to guarantee access to the reference catalogs ([Glottolog](https://glottolog.org), [Concepticon](https://concepticon.clld.org) and [CLTS](https://clts.clld.org)), please follow the installation instructions for the [pylexibank package](https://github.com/lexibank/pylexibank), or see the [instructions for cldfbench](https://github.com/cldf/cldfbench/#catalogs), which provide more detail. 

4. Now we can plot the varieties on a map (see Figure 1):
   ```shell
   $ cldfbench seabor.plotlanguages
   ```
   As well as recreate other figures from the paper.
   ```shell
   $ cldfbench seabor.plotmaps --concepts name flower correctright
   $ cldfbench seabor.piechart
   ```

5. And you can also check for the significance with respect to the stability of certain concept lists.
   ```shell
   $ cldfbench seabor.distribution --conceptlist Swadesh-1955-100 --runs 10000
   Conceptlist            Proportion of Non-Borrowed Items    Number of Items
   -------------------  ----------------------------------  -----------------
   Swadesh-1955-100                                   0.81                 78
   != Swadesh-1955-100                                0.74                172
   Significance: 0.0300 (0.0688)
   $ cldfbench seabor.distribution --conceptlist Tadmor-2009-100 --runs 10000
   Conceptlist           Proportion of Non-Borrowed Items    Number of Items
   ------------------  ----------------------------------  -----------------
   Tadmor-2009-100                                   0.80                 61
   != Tadmor-2009-100                                0.74                189
   Significance: 0.0711 (0.0590)  
   ```
   Note that again the results may slightly differ, due to the randomization process.