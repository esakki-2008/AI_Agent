# ClipForge AI — Commercial Launch Checklist

## Product package

- [x] Version: 1.0.0
- [x] Windows setup script
- [x] Windows start script
- [x] Installation guide
- [x] Product manifest
- [x] Changelog
- [x] Commercial license
- [x] Package builder script
- [x] Frontend production build tested
- [x] No API key required for the local AI workflow

## Gumroad

1. Connect an eligible payout method.
2. Upload the ZIP created by `package_windows.bat` to the product Content section.
3. Keep the price at **$19** for the initial launch.
4. Use the prepared product description.
5. Select a clear refund policy before publishing.
6. Publish the product when Gumroad allows it.
7. Copy the final public product URL.

## Website checkout

`frontend/src/PaymentCTA.jsx` contains the checkout button. The public Gumroad URL should be inserted only after the final product URL exists.

Do not put private payment credentials, bank details, API keys, or secrets into the repository.

## Customer delivery

The Gumroad download should contain the source package and documentation needed to install and run ClipForge AI locally on Windows.

## Important product limitations to communicate honestly

- ClipForge AI is a local Windows application; it is not a hosted SaaS service.
- YouTube downloading depends on the availability and terms of the source platform.
- Users are responsible for having rights to the media they process.
- Face-aware framing uses local face detection to choose a stable crop position; it is not continuous identity tracking.
- Platform presets adjust supported ClipForge settings; they do not publish directly to social platforms.
- The current package does not include a standalone EXE installer.
