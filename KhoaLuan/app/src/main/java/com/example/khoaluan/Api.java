package com.example.khoaluan;

import java.util.List;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;

public interface Api {
    static final String BASE_URL = "http://yung575451.pythonanywhere.com/api/login";
    @GET("/api/login/")
    Call<LoginResponse> loginUser(@Body LoginRequest loginRequest);
}