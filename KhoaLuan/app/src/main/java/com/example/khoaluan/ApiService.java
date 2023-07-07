package com.example.khoaluan;

import android.graphics.Bitmap;
import android.util.Base64;

import java.io.ByteArrayOutputStream;
import java.io.IOException;

import okhttp3.FormBody;
import okhttp3.HttpUrl;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

public class ApiService {
    private static final String BASE_URL = "http://yung575451.pythonanywhere.com";
    private OkHttpClient client;

    public ApiService() {
        client = new OkHttpClient();
    }

    public String login(String account, String password) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(BASE_URL + "/api/login").newBuilder();
        urlBuilder.addQueryParameter("account", account);
        urlBuilder.addQueryParameter("password", password);
        String url = urlBuilder.build().toString();

        Request request = new Request.Builder().url(url).build();
        Response response = client.newCall(request).execute();

        if (response.isSuccessful()) {
            return response.body().string();
        } else if (response.code() == 401) {
            throw new UnauthorizedException("Invalid username or password");
        } else {
            throw new IOException("Error: " + response);
        }
    }

    public String check_in_check(String eid) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(BASE_URL + "/api/check_in_checker").newBuilder();
        urlBuilder.addQueryParameter("eid", eid);
        String url = urlBuilder.build().toString();

        Request request = new Request.Builder().url(url).build();
        Response response = client.newCall(request).execute();

        if (response.isSuccessful()) {
            return response.body().string();
        } else if (response.code() == 401) {
            throw new UnauthorizedException("Error Employee in database");
        } else {
            throw new IOException("Error: " + response);
        }
    }


    public String bitmapToBase64(Bitmap bitmap) {
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, byteArrayOutputStream);
        byte[] byteArray = byteArrayOutputStream.toByteArray();
        return Base64.encodeToString(byteArray, Base64.DEFAULT);
    }

    public String check_in_face(String faceEncode,String eid,String checkType) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(BASE_URL + "/api-endpoint").newBuilder();
        String url = urlBuilder.build().toString();

        // create a FormBody with your 'eid' parameter
        FormBody formBody = new FormBody.Builder()
                .add("eid", eid) // Add the 'eid' parameter
                .add("checkType", checkType) // Add the 'checkType' parameter
                .add("image", faceEncode)
                .build();

        // pass this formBody as the POST body in the request
        Request request = new Request.Builder()
                .url(url)
                .post(formBody)
                .build();

        Response response = client.newCall(request).execute();

        if (response.isSuccessful()) {
            return response.body().string();
        } else if (response.code() == 401) {
            throw new UnauthorizedException("Error Employee in database");
        } else {
            throw new IOException("Error: " + response);
        }
    }

}
