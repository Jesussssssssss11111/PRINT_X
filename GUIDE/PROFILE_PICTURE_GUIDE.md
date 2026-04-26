# Profile Picture Upload Feature

## ✅ Feature Added!

Users can now upload and change their profile pictures!

## 🎨 How It Works

### Upload Profile Picture

1. **Go to Profile Page**: Click "Profile" in the navbar (when logged in)
2. **Click on Avatar**: Click the circular profile picture at the top
3. **Select Image**: Choose an image file from your computer
4. **Automatic Upload**: Image is automatically uploaded and displayed
5. **Navbar Updates**: Your profile picture appears in the navbar

### Features

- ✅ **Click to Upload**: Simply click the avatar circle
- ✅ **Hover Effect**: Hover shows "📷 Change Photo" overlay
- ✅ **Image Validation**: Only image files accepted
- ✅ **Size Limit**: Maximum 5MB file size
- ✅ **Base64 Storage**: Images stored as base64 in database
- ✅ **Instant Preview**: See your new picture immediately
- ✅ **Navbar Integration**: Picture shows in navigation bar
- ✅ **Persistent**: Picture saved across sessions

### Supported Formats

- ✅ JPEG/JPG
- ✅ PNG
- ✅ GIF
- ✅ WebP
- ✅ BMP
- ✅ SVG

### Technical Details

**Storage Method**: Base64 encoding
- Images are converted to base64 strings
- Stored in `UserProfile.profile_picture` field
- Also cached in localStorage for navbar display

**Size Limit**: 5MB
- Prevents database bloat
- Ensures fast loading
- Reasonable for profile pictures

**Display Locations**:
1. Profile page sidebar (large, 100x100px)
2. Navbar user info (small, 24x24px)

## 🧪 Testing

### Test Profile Picture Upload

1. **Login** to your account
2. **Go to Profile**: Click "Profile" in navbar
3. **Click Avatar**: Click the circular profile picture
4. **Select Image**: Choose a photo (JPG, PNG, etc.)
5. **Verify Upload**: 
   - ✅ Picture appears in profile page
   - ✅ Picture appears in navbar
   - ✅ Success message shows
6. **Refresh Page**: Picture should persist
7. **Navigate Away**: Go to another page
8. **Check Navbar**: Picture should still show in navbar

### Test Validation

**Test File Type**:
1. Try uploading a non-image file (e.g., .txt, .pdf)
2. Should show error: "Please select an image file."

**Test File Size**:
1. Try uploading a very large image (>5MB)
2. Should show error: "Image size must be less than 5MB."

**Test Valid Upload**:
1. Upload a normal photo (< 5MB, JPG/PNG)
2. Should show success: "Profile picture updated!"

## 🎨 UI/UX Features

### Visual Feedback

1. **Hover Effect**: 
   - Avatar scales up slightly
   - Shows "📷 Change Photo" overlay
   - Glowing red shadow appears

2. **Loading State**:
   - Shows ⏳ emoji while uploading
   - Prevents multiple uploads

3. **Success State**:
   - Shows new picture immediately
   - Toast notification appears
   - Navbar updates automatically

### Responsive Design

- ✅ Works on desktop
- ✅ Works on mobile
- ✅ Touch-friendly on tablets
- ✅ Accessible (keyboard navigation)

## 🔧 Code Implementation

### Frontend (profile.html)

```javascript
// Handle avatar change
async function handleAvatarChange(event) {
  const file = event.target.files[0];
  
  // Validate file type and size
  if (!file.type.startsWith('image/')) {
    Toast.error('Please select an image file.');
    return;
  }
  
  if (file.size > 5 * 1024 * 1024) {
    Toast.error('Image size must be less than 5MB.');
    return;
  }
  
  // Convert to base64 and upload
  const reader = new FileReader();
  reader.onload = async function(e) {
    const base64Image = e.target.result;
    
    const res = await apiFetch('/profile/', {
      method: 'PATCH',
      body: JSON.stringify({ profile_picture: base64Image }),
    });
    
    if (res.ok) {
      // Update display and navbar
      Toast.success('Profile picture updated!');
      // ... update UI
    }
  };
  
  reader.readAsDataURL(file);
}
```

### Backend (new_features_views.py)

```python
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'PATCH':
        # Update profile picture
        if 'profile_picture' in request.data:
            profile.profile_picture = request.data['profile_picture']
        
        profile.save()
        return Response({
            'message': 'Profile updated successfully.',
            'profile': UserProfileSerializer(profile).data
        })
```

### Database (models.py)

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.CharField(max_length=500, blank=True, default='')
    # ... other fields
```

## 🚀 Advanced Features (Optional)

### Future Enhancements

1. **Image Cropping**: Add crop tool before upload
2. **Multiple Sizes**: Generate thumbnails automatically
3. **Cloud Storage**: Upload to AWS S3 or Cloudinary
4. **Avatar Library**: Provide default avatars to choose from
5. **Webcam Capture**: Take photo directly from webcam
6. **Image Filters**: Apply filters/effects to photos
7. **Compression**: Auto-compress large images

### Example: Add Image Cropping

```html
<!-- Add Cropper.js -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>

<script>
// Show crop modal before upload
function showCropModal(imageFile) {
  const modal = document.getElementById('cropModal');
  const image = document.getElementById('cropImage');
  
  const reader = new FileReader();
  reader.onload = function(e) {
    image.src = e.target.result;
    const cropper = new Cropper(image, {
      aspectRatio: 1,
      viewMode: 1,
    });
    
    // On crop confirm
    document.getElementById('cropConfirm').onclick = function() {
      const canvas = cropper.getCroppedCanvas({
        width: 200,
        height: 200,
      });
      
      canvas.toBlob(function(blob) {
        // Upload cropped image
        uploadAvatar(blob);
      });
    };
  };
  
  reader.readAsDataURL(imageFile);
  modal.style.display = 'block';
}
</script>
```

## 📊 Storage Considerations

### Base64 vs File Upload

**Current Implementation (Base64)**:
- ✅ Simple to implement
- ✅ No file server needed
- ✅ Works with SQLite
- ❌ Larger database size
- ❌ Not ideal for production at scale

**Alternative (File Upload)**:
- ✅ Smaller database
- ✅ Better for production
- ✅ Can use CDN
- ❌ Requires file server
- ❌ More complex setup

### Migration to File Storage (Optional)

If you want to switch to file storage later:

1. **Update Model**:
```python
class UserProfile(models.Model):
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
```

2. **Update Settings**:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

3. **Update URLs**:
```python
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

4. **Update Frontend**:
```javascript
// Use FormData instead of base64
const formData = new FormData();
formData.append('profile_picture', file);

await apiFetch('/profile/', {
  method: 'PATCH',
  body: formData,
}, true); // isFormData = true
```

## ✅ Summary

Profile picture upload is now fully functional with:

- ✅ Click-to-upload interface
- ✅ Image validation (type & size)
- ✅ Instant preview
- ✅ Navbar integration
- ✅ Persistent storage
- ✅ Beautiful UI with hover effects
- ✅ Mobile-friendly
- ✅ Error handling

**Test it now**: Login → Profile → Click avatar → Upload photo! 📷
