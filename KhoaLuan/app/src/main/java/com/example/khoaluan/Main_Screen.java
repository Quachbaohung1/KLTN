package com.example.khoaluan;

import static android.content.ContentValues.TAG;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;

import androidx.activity.result.ActivityResult;
import androidx.activity.result.ActivityResultCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.constraintlayout.widget.ConstraintLayout;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;
import androidx.viewpager.widget.ViewPager;

import android.Manifest;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class Main_Screen  extends AppCompatActivity {

    private int currentPage;

    private static final int REQUEST_IMAGE_CAPTURE = 1;

    private static final int REQUEST_PERMISSIONS = 1234;
    private static final String[] PERMISSIONS = {
            Manifest.permission.CAMERA,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE
    };

    private String check;

    private Bitmap imageBitmap;

    private String combined;

    private Integer success=0;

    // Define mGetContent here, at the class level
    private Uri photoUri;
    private ActivityResultLauncher<Intent> mGetContent;

    private ApiService apiService;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        apiService = new ApiService();
        setContentView(R.layout.camera_main_screen);
        ProgressBar loadingIndicator = findViewById(R.id.loadingIndicator);
        loadingIndicator.setVisibility(View.VISIBLE);
        Button checkInButton=findViewById(R.id.button_camera);
        ConstraintLayout buttonlayout=findViewById(R.id.btn_layout);
        String eidtext= SharedPrefManager.getInstance(this).getUsername();
        new Thread(() -> {
            try {
                String response = apiService.check_in_check(eidtext);
                JSONObject jsonResponse = new JSONObject(response);
                String checker = jsonResponse.getString("result");
                Log.d(TAG, "Login failed: " + checker);
                if (checker.equals("please check in")) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            // Modify the view here
                            check="check_in";
                            checkInButton.setText("Check In");
                            loadingIndicator.setVisibility(View.GONE);
                            buttonlayout.setVisibility(View.VISIBLE);
                        }
                    });
                } else {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            // Modify the view here
                            check="check_out";
                            checkInButton.setText("Check Out");
                            loadingIndicator.setVisibility(View.GONE);
                            buttonlayout.setVisibility(View.VISIBLE);
                        }
                    });
                }
            } catch (UnauthorizedException e) {
                Log.e(TAG, "Error: ", e);
                showError("Invalid username or password");
            } catch (IOException | JSONException e) {
                Log.e(TAG, "Error: ", e);
                showError("An error occurred while logging in. Please try again later.");
            }
        }).start();
        Button signOut=findViewById(R.id.button_signout);
        Button confirm_image_btn=findViewById(R.id.confirm_button);
        TextView eid=findViewById(R.id.eidTV);
        eid.setText(eidtext);

        // Initialize mGetContent inside onCreate
        mGetContent = registerForActivityResult(new ActivityResultContracts.StartActivityForResult(),
                new ActivityResultCallback<ActivityResult>() {
                    @Override
                    public void onActivityResult(ActivityResult result) {
                        if (result.getResultCode() == Activity.RESULT_OK) {
                            // Read the photo from photoUri
                            try {
                                int desiredWidth = 450;
                                int desiredHeight = 450;

                                BitmapFactory.Options options = new BitmapFactory.Options();
                                options.inJustDecodeBounds = true; // Retrieve image dimensions only
                                BitmapFactory.decodeStream(getContentResolver().openInputStream(photoUri), null, options);

                                int imageWidth = options.outWidth;
                                int imageHeight = options.outHeight;

                                int scaleFactor = Math.min(imageWidth / desiredWidth, imageHeight / desiredHeight);

                                options.inJustDecodeBounds = false;
                                options.inSampleSize = scaleFactor;


                                Bitmap originalBitmap = BitmapFactory.decodeStream(getContentResolver().openInputStream(photoUri), null, options);

                                Matrix matrix = new Matrix();
                                matrix.postRotate(90); // Rotate by 90 degrees

                                imageBitmap = Bitmap.createBitmap(originalBitmap, 0, 0, originalBitmap.getWidth(), originalBitmap.getHeight(), matrix, true);

                                ImageView imageView = findViewById(R.id.image_view);
                                imageView.setImageBitmap(imageBitmap);
                                imageView.setVisibility(View.VISIBLE);
                                confirm_image_btn.setVisibility(View.VISIBLE);
                                checkInButton.setText("Retake Image");
                                success = 0;
                            } catch (IOException e) {
                                // Handle error here
                                Log.e(TAG, "Error reading bitmap", e);
                            }
                        }
                    }
                });

        checkInButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (checkPermissions()) {
                    dispatchTakePictureIntent();
                }
            }
        });

        signOut.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                // Logout user and go back to LoginActivity
                SharedPrefManager.getInstance(Main_Screen.this).logout();
                startActivity(new Intent(Main_Screen.this, MainActivity.class));
                finish();
            }
        });

        confirm_image_btn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                confirmloadingwait(loadingIndicator,buttonlayout);
                if(success==1){
                    combined="You have Already "+check+" with this user";
                    Toast.makeText(Main_Screen.this, combined, Toast.LENGTH_SHORT).show();
                    confirmloadingfinish(loadingIndicator,buttonlayout);
                    return;
                }
                else{
                    String imagebase64=apiService.bitmapToBase64(imageBitmap);
                    new Thread(() -> {
                        try {
                            combined = "eid: " + eidtext + ", check: " + check;
                            Log.d("package send", combined);
                            String response = apiService.check_in_face(imagebase64,eidtext,check);
                            JSONObject jsonResponse = new JSONObject(response);
                            String msg = jsonResponse.getString("msg");
                            String width= jsonResponse.getString("width");
                            String height = jsonResponse.getString("height");
                            String result = jsonResponse.getString("status");
                            String ManagerId = jsonResponse.getString("manager_Id");
                            String customerId = jsonResponse.getString("customer_id_recognize");
                            combined = ", status: "+result+", manager_Id: "+ManagerId+", customerId: "+customerId;
                            if (msg.equals("success")) {
                                runOnUiThread(() -> {
                                    // Show an error message, e.g., using a Toast
                                    Toast.makeText(Main_Screen.this, combined, Toast.LENGTH_SHORT).show();
                                    success = 1;
                                    confirmloadingfinish(loadingIndicator,buttonlayout);
                                });
                            } else {
                                Log.d(TAG, "Login failed: " + msg);
                                confirmloadingfinish(loadingIndicator,buttonlayout);
                            }
                        } catch (UnauthorizedException e) {
                            Log.e(TAG, "Error: ", e);
                            showError("Invalid username or password");
                            confirmloadingfinish(loadingIndicator,buttonlayout);
                        } catch (IOException | JSONException e) {
                            Log.e(TAG, "Error: ", e);
                            showError("An error occurred while logging in. Please try again later.");
                            confirmloadingfinish(loadingIndicator,buttonlayout);
                        }
                    }).start();
                }
            }
        });
    }
    // Your other functions (checkPermissions, dispatchTakePictureIntent, createImageFile, cropSquareBitmap, etc.)
    private void dispatchTakePictureIntent() {
        Intent takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
            // Create the File where the photo should go
            File photoFile = null;
            try {
                photoFile = createImageFile();
                // Save a file: path for use with ACTION_VIEW intents
                photoUri = FileProvider.getUriForFile(this, "com.example.android.fileprovider", photoFile);
            } catch (IOException ex) {
                // Error occurred while creating the File
                Log.e(TAG, "An error occurred while creating the file", ex);
            }
            // Continue only if the File was successfully created
            if (photoFile != null) {
                takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, photoUri);
                mGetContent.launch(takePictureIntent);
            }
        }
    }

    private File createImageFile() throws IOException {
        File storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
        File imageFile = new File(storageDir, "holder.jpg");
        if (imageFile.exists()) {
            imageFile.delete();
        }
        imageFile.createNewFile();
        return imageFile;
    }

    private boolean checkPermissions() {
        for (String permission : PERMISSIONS) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, PERMISSIONS, REQUEST_PERMISSIONS);
                return false;
            }
        }
        return true;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_PERMISSIONS) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                dispatchTakePictureIntent();
            } else {
                // Handle the feature without camera functionality or close the app
            }
        }
    }

    private void showError(String message) {
        runOnUiThread(() -> {
            // Show an error message, e.g., using a Toast
            Toast.makeText(Main_Screen.this, message, Toast.LENGTH_SHORT).show();
        });
    }

    private void confirmloadingwait (ProgressBar x, ConstraintLayout y){
        y.setAlpha(0.3f);
        x.setVisibility(View.VISIBLE);
    }

    private void confirmloadingfinish (ProgressBar x, ConstraintLayout y){
        y.setAlpha(1f);
        x.setVisibility(View.INVISIBLE);
    }

    private Bitmap resizeAndCropBitmap(Bitmap originalBitmap, int desiredWidth, int desiredHeight) {
        int originalWidth = originalBitmap.getWidth();
        int originalHeight = originalBitmap.getHeight();

        float scaleWidth = (float) desiredWidth / originalWidth;
        float scaleHeight = (float) desiredHeight / originalHeight;
        float scaleFactor = Math.max(scaleWidth, scaleHeight);

        int scaledWidth = (int) (originalWidth * scaleFactor);
        int scaledHeight = (int) (originalHeight * scaleFactor);

        Bitmap scaledBitmap = Bitmap.createScaledBitmap(originalBitmap, scaledWidth, scaledHeight, true);

        int offsetX = (scaledWidth - desiredWidth) / 2;
        int offsetY = (scaledHeight - desiredHeight) / 2;

        Bitmap croppedBitmap = Bitmap.createBitmap(scaledBitmap, offsetX, offsetY, desiredWidth, desiredHeight);

        return croppedBitmap;
    }


}

