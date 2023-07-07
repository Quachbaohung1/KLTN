package com.example.khoaluan;

import androidx.appcompat.app.AppCompatActivity;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.util.Log;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.Toast;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;

import retrofit2.Callback;

import retrofit2.Call;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity implements View.OnClickListener {

    private EditText userName;
    private EditText password;
    private Button login;

    private ImageView showpassword;
    private Integer showpasscheck;
    private String user;
    private String pass;

    private static final String TAG = "MainActivity";
    private ApiService apiService;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);
        userName=findViewById(R.id.username);

        showpasscheck=0;

        password=findViewById(R.id.password);
        login=findViewById(R.id.login_button);
        showpassword = findViewById(R.id.showaccount);
        apiService = new ApiService();

        // Check if user is already logged in
        if (SharedPrefManager.getInstance(this).isLoggedIn()) {
            // User is already logged in, navigate to MainScreenActivity
            startActivity(new Intent(this, Main_Screen.class));
            finish();
        }

        login.setOnClickListener(this);
        showpassword.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                int inputType = password.getInputType();
                if (inputType == InputType.TYPE_TEXT_VARIATION_PASSWORD) {
                    password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
                    password.setTransformationMethod(PasswordTransformationMethod.getInstance());
                } else {
                    password.setInputType(InputType.TYPE_TEXT_VARIATION_PASSWORD);
                    password.setTransformationMethod(null);
                }

                // Set the cursor to the end of the text
                password.setSelection(password.getText().length());
            }
        });
    }

    @Override
    public void onClick(View v) {
        String account = userName.getText().toString();
        String pass = password.getText().toString();

        new Thread(() -> {
            try {
                String response = apiService.login(account, pass);
                JSONObject jsonResponse = new JSONObject(response);
                String msg = jsonResponse.getString("msg");
                String eid= jsonResponse.getString("id");
                if (msg.equals("Logged in successfully")) {
                    // Perform your action here
                    SharedPrefManager.getInstance(MainActivity.this).userLogin(eid);
                    startActivity(new Intent(MainActivity.this, Main_Screen.class));
                    finish();
                } else {
                    Log.d(TAG, "Login failed: " + msg);
                }
            } catch (UnauthorizedException e) {
                Log.e(TAG, "Error: ", e);
                showError("Invalid username or password");
            } catch (IOException | JSONException e) {
                Log.e(TAG, "Error: ", e);
                showError("An error occurred while logging in. Please try again later.");
            }
        }).start();
    }

    private void showError(String message) {
        runOnUiThread(() -> {
            // Show an error message, e.g., using a Toast
            Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show();
        });
    }
}