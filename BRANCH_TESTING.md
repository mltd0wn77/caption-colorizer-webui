# Testing the Font & Color Customization Branch on Render

## 🚀 How to Deploy and Test the New Features

### Option 1: Deploy the Branch Directly on Render (Recommended for Testing)

1. **Go to your Render Dashboard**
   - Visit https://dashboard.render.com
   - Find your `caption-colorizer-webui` service

2. **Change the Branch**
   - Go to Settings → Build & Deploy
   - Under "Branch", change from `main` to `font-color-customization`
   - Click "Save Changes"

3. **Manual Deploy**
   - Click "Manual Deploy" → "Deploy latest commit"
   - Wait for the build to complete (3-5 minutes)

4. **Test the New Features**
   - Visit your app URL
   - You'll see the enhanced UI with:
     - **Color Customization Section**: 5 color pickers (1 base + 4 accents) with hex input fields
     - **Custom Font Upload**: Upload TTF/OTF files
     - **Better Progress Tracking**: Shows elapsed time and percentage
     - **Download Button**: No more auto-download, click when ready
     - **Session Persistence**: Can switch tabs and come back

### Option 2: Create a Separate Test Service

If you want to keep your main service running on the stable version:

1. **Create a New Web Service on Render**
   - Click "New +" → "Web Service"
   - Connect the same repository
   - Name it something like `caption-colorizer-test`
   - **Important**: Select branch `font-color-customization`
   - Use the same settings as your main service

2. **Deploy and Test**
   - Let it auto-deploy
   - You'll get a new URL like `https://caption-colorizer-test.onrender.com`
   - Test all new features there

## 🎨 What's New to Test

### 1. **Custom Colors**
- Try changing the accent colors using the color pickers
- Type hex codes directly (e.g., #FF0000 for red)
- The colors should sync between picker and text input
- Test that captions use your custom colors correctly

### 2. **Custom Font Upload**
- Upload a TTF or OTF font file
- The captions should use your uploaded font
- Verify fonts are not italic anymore (fixed!)
- Test with different font weights

### 3. **Improved Font Selection**
- Even without custom font, the default should:
  - Be bold (weight 700), not italic
  - Show ALL CAPS properly
  - Have better readability

### 4. **Better Color Rendering**
- Colors should be accurate to your hex codes
- No more "flashy" or washed-out colors
- Proper opacity and contrast

### 5. **UI/UX Improvements**
- Progress bar with elapsed time
- Download button (no auto-download)
- Session persistence (can switch tabs)
- Better visual organization

## 🧪 Testing Checklist

- [ ] Upload video and SRT files
- [ ] Change all 5 colors and verify they apply
- [ ] Upload a custom font and verify it's used
- [ ] Check that text is ALL CAPS
- [ ] Verify font is bold, not italic
- [ ] Test switching browser tabs during processing
- [ ] Verify download button appears when complete
- [ ] Check that colors match the hex codes exactly
- [ ] Test with different video resolutions
- [ ] Verify the XML file is XMEML format (for Premiere)

## ✅ After Testing

If everything works well:

1. **Merge to Main** (when you're ready)
   ```bash
   # I'll do this for you when you confirm
   git checkout main
   git merge font-color-customization
   git push origin main
   ```

2. **Switch Render Back to Main**
   - Go to Settings → Build & Deploy
   - Change branch back to `main`
   - Deploy

## 🐛 If You Find Issues

Just let me know what's not working and I'll fix it immediately in the branch before merging!

## 📝 Notes

- The enhanced text renderer (`text_render_enhanced.py`) is only used when:
  - A custom font is uploaded, OR
  - The `USE_ENHANCED_RENDERER` environment variable is set
- This ensures backward compatibility with the original renderer
- All changes are isolated to the branch until you explicitly confirm the merge
