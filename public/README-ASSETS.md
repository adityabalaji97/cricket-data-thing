# Cricket Data Thing - SVG Assets

These SVG files need to be converted to the appropriate formats:

1. cricket-icon.svg -> cricket-icon.ico (favicon)
2. cricket-logo192.svg -> cricket-logo192.png (app icon)
3. cricket-logo512.svg -> cricket-logo512.png (app icon)
4. cricket-og-image.svg -> cricket-og-image.png (social sharing)

You can use online converters like https://convertio.co/svg-ico/ and https://svgtopng.com/ to convert these files.

Once converted, place them in the /public directory of your project.

## Important Note

Until the conversions are done, you can temporarily use the SVG files directly in your HTML by changing the file references:

In index.html:
```html
<link rel="icon" href="%PUBLIC_URL%/cricket-icon.svg" />
<link rel="apple-touch-icon" href="%PUBLIC_URL%/cricket-logo192.svg" />
```

In manifest.json:
```json
{
  "icons": [
    {
      "src": "cricket-icon.svg",
      "sizes": "64x64 32x32 24x24 16x16",
      "type": "image/svg+xml"
    },
    ...
  ]
}
```

However, for production, it's better to use the converted files in the formats specified in the configuration files.
