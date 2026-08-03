# Standard Blueprint: UI/UX & Mobile First

## 1. Grid & Layouts
- **Mobile First**: Default to `grid-cols-1`. Expand to `md:grid-cols-4` for tablet/desktop.
- **Touch Targets**: Interactive elements must have a minimum clickable area of 44x44px. Use padding or pseudo-elements to extend hit areas if visual size is smaller.

## 2. Image & Media Handling
- **Lightbox Standard**: All media galleries must implement the native JS Lightbox system.
    - **Backdrop**: `bg-black/90` with `backdrop-blur-sm`.
    - **Controls**: Clear "CLOSE" button.
    - **Video**: Auto-play with controls when expanded.
    - **Scroll Lock**: Body scroll must be locked (`overflow: hidden`) when modal is open.

## 3. Forms & Uploads
- **Zero-Click**: File inputs should trigger auto-upload on `change` event for smoother mobile flow.
- **Feedback**: Immediate opacity change or loader to indicate processing.
