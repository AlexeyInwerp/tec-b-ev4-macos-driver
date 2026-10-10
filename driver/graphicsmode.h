// Graphics Mode, offered only for the older printers in this set.
//
// The B-EV4 documents TOPIX compression and handles every job with it, so its
// PPDs omit this option altogether. The other choices only ever made the data
// bigger - 119 KB raw and 251 KB banded against 9.7 KB for the same label - and
// the banded mode, built as a fix for the raw socket port dropping jobs, did not
// fix it. Other models are left exactly as they were: their behaviour with
// these modes is not something that can be tested here.
//
// ppdc cannot override an inherited option (redefining one just appends
// duplicate choices), so this is included per family rather than defined
// globally and removed for the B-EV4.
Group "InstallableOptions/Installable Options"
  Option "teGraphicsMode/Graphics Mode" PickOne AnySetup 20
    *Choice "1/TOPIX Compression" ""
    Choice "2/Raw 8bit Graphics (overwrite)" ""
    Choice "3/Raw 8bit Graphics (logic OR)" ""
    Choice "4/Banded nibble (uncompressed, small commands)" ""
