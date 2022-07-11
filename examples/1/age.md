# Analysis of `png` style `ts` in AGE

_Some data sources in AGE use the **steganographically written `ts` in `png`**_

Here is an example (see `age.ts` for more).

```
8950 4e47 0d0a 1a0a // PNG identifier

0000 000d // Block length
4948 4452 // "IHDR"
0000 0001 // width
0000 0001 // height
08        // bit depth, 08=grayscale 8bits
06        // ColorType, I Don't know why it's '6'
00        // Compression method
00        // Filter method
00        // Interlace method
1f15 c489 // CRC

0000 000d // Block length
4944 4154 // "IDAT"
78da 637c f3eb 573d 0009 1b03 61 // 13bytes data
627c ad85 // CRC

0000 0000 // Block length
4945 4e44 // "IEND"
ae42 6082 // CRC

// This line down is the actual ts file
// Tips: ts file has its own structure.
// The distinctive feature of a ts pack is that the first byte is 47, and its size is fixed at 188 bytes.
4740 1110 0042 f025 0001 c100 00ff 01ff
...
```

This ts file `age.ts` is the 104th ts file of the m3u8 file that is from the second episode of ["Kiznaiver" (羁绊者)](https://www.agemys.cc/detail/20160078) on [age](https://www.agefans.cc).
