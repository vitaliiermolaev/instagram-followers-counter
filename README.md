# Instagram Followers Counter

A BUSY Bar app that shows the follower count of a public Instagram profile.

- Front display: the Instagram logo, the username in caps and the follower count, rounded the way Instagram shows it (`686M`, `19.8K`, `5,017`). A long username scrolls.
- Hearts float up in the bottom-right corner next to the count.
- The background, the icon and the hearts follow the Figma design (`src/images/bg.png`, `tools/hearts.py`).
- Back display: mirrors the front one.
- The count updates every 15 minutes. If an update fails, the last count stays on screen with a red cross on the logo, and the app tries again in 5 minutes.
- Back closes the app.

## Settings

**Instagram profile**: a profile link or a username, for example `https://www.instagram.com/instagram/`, `instagram.com/instagram` or `@instagram`. Edit it in the BUSY app or in the bar's web interface. The bar picks up a new value within 10 seconds.

## How it works

The app needs no Instagram account or token. It loads the public profile page `https://www.instagram.com/<username>/` and reads the follower count from the page's `og:description` meta tag:

```
104M Followers, 95 Following, 5,017 Posts - See Instagram photos and videos from NASA (@nasa)
```

The request carries the app's own `User-Agent`. With a browser one, which is the firmware default, Instagram returns an empty app shell without the profile data.

The page is about 0.5–0.7 MB. The app reads it as a stream, searches only until the tag is found and drops the rest chunk by chunk, so it fits in the app's memory.

Instagram returns the same empty shell for a profile that doesn't exist. The app then shows "Not found". If the page layout changes, the app stops finding the count.

## Hearts animation

`src/animations/hearts.anim` is built from `tools/hearts.py` with `scripts/seq2anim.py` from the [BUSY Bar firmware](https://github.com/busy-app/busybar-firmware). Both need Pillow:

```sh
python3 tools/hearts.py build/
python3 <firmware>/scripts/seq2anim.py -o src/animations/hearts.anim build/hearts_17x16.zip
```

## Build and install

Connect the bar over USB, then:

```sh
npm ci
npx busy-cli build
npx busy-cli app stop
npx busy-cli app install
npx busy-cli app run
```

On macOS build with `COPYFILE_DISABLE=1`, otherwise `._*` files end up in the package.
