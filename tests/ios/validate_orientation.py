"""Run on macOS with Xcode CLI tools: python3 tests/ios/validate_orientation.py.

Exercise the exact production normalization method using CoreImage and a small
UIImage adapter, without building or launching the Cordova app. Verify every
EXIF rotation/reflection and the front-camera horizontal mirror with asymmetric
pixels. This does not test camera hardware, scene selection, or UIKit decoding.
"""
from pathlib import Path
import subprocess
import tempfile
source=(Path(__file__).resolve().parents[2] / 'src/ios/CameraPreview.m').read_text()
method=source[source.index('- (CIImage *)orientedImageFromImage:'):source.index('- (void) invokeTapToFocus:')]
preamble=r'''
#import <Foundation/Foundation.h>
#import <CoreImage/CoreImage.h>
#import <CoreGraphics/CoreGraphics.h>
typedef NS_ENUM(NSInteger, UIImageOrientation) {
 UIImageOrientationUp, UIImageOrientationDown, UIImageOrientationLeft, UIImageOrientationRight,
 UIImageOrientationUpMirrored, UIImageOrientationDownMirrored, UIImageOrientationLeftMirrored, UIImageOrientationRightMirrored
};
@interface UIImage : NSObject
@property CGImageRef CGImage;
@property UIImageOrientation imageOrientation;
@end
@implementation UIImage
@end
@interface CameraPreview : NSObject
- (CIImage *)orientedImageFromImage:(UIImage *)image;
@end
@implementation CameraPreview
'''
harness=r'''
@end
int main(void) { @autoreleasepool {
 unsigned char pixels[] = {40,0,0,255,80,0,0,255,120,0,0,255,160,0,0,255,200,0,0,255,240,0,0,255};
 CGColorSpaceRef cs=CGColorSpaceCreateDeviceRGB();
 CGDataProviderRef provider=CGDataProviderCreateWithData(NULL,pixels,sizeof(pixels),NULL);
 CGImageRef raw=CGImageCreate(3,2,8,32,12,cs,kCGBitmapByteOrder32Big|kCGImageAlphaPremultipliedLast,provider,NULL,NO,kCGRenderingIntentDefault);
 UIImage *image=[UIImage new]; image.CGImage=raw;
 CameraPreview *plugin=[CameraPreview new];
 CIContext *context=[CIContext contextWithOptions:@{kCIContextUseSoftwareRenderer:@YES,kCIContextWorkingColorSpace:[NSNull null],kCIContextOutputColorSpace:[NSNull null]}];
 UIImageOrientation orientations[]={UIImageOrientationUp,UIImageOrientationUpMirrored,UIImageOrientationDown,UIImageOrientationDownMirrored,UIImageOrientationLeftMirrored,UIImageOrientationRight,UIImageOrientationRightMirrored,UIImageOrientationLeft};
 int expected[][6]={{1,2,3,4,5,6},{3,2,1,6,5,4},{6,5,4,3,2,1},{4,5,6,1,2,3},{1,4,2,5,3,6},{4,1,5,2,6,3},{6,3,5,2,4,1},{3,6,2,5,1,4}};
 for(int i=0;i<8;i++) {
  image.imageOrientation=orientations[i];
  CIImage *oriented=[plugin orientedImageFromImage:image];
  int w=i<4?3:2,h=i<4?2:3;
  if(oriented.extent.size.width!=w || oriented.extent.size.height!=h) return 10+i;
  for(int mirrored=0;mirrored<2;mirrored++) {
   CIImage *result=oriented;
   if(mirrored) {
    CGAffineTransform matrix=CGAffineTransformMake(-1,0,0,1,CGRectGetMinX(result.extent)+CGRectGetMaxX(result.extent),0);
    result=[result imageByApplyingTransform:matrix];
   }
   unsigned char output[24]={0};
   [context render:result toBitmap:output rowBytes:w*4 bounds:result.extent format:kCIFormatRGBA8 colorSpace:NULL];
   for(int j=0;j<6;j++) {
    int index=mirrored?(j/w)*w+(w-1-j%w):j;
    if(abs(output[j*4]-expected[i][index]*40)>1) {
     fprintf(stderr,"FAIL EXIF %d mirror %d pixel %d: got %d expected %d\n",i+1,mirrored,j,output[j*4],expected[i][index]*40);return 30+i;
    }
   }
  }
 }
 puts("PASS: exact production normalization method, all 8 orientations, dimensions and horizontal front-camera mirroring (16 image cases).");
 CGImageRelease(raw);CGDataProviderRelease(provider);CGColorSpaceRelease(cs);
 } return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='camera-orientation-') as temporary:
    directory = Path(temporary)
    harness_path = directory / 'orientation.m'
    executable_path = directory / 'orientation'
    harness_path.write_text(preamble + method + harness)
    subprocess.run([
        'xcrun', 'clang', '-fobjc-arc',
        '-framework', 'Foundation', '-framework', 'CoreImage',
        '-framework', 'CoreGraphics', str(harness_path), '-o', str(executable_path)
    ], check=True)
    subprocess.run([str(executable_path)], check=True)
