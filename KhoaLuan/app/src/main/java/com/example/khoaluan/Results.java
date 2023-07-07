package com.example.khoaluan;

import com.google.gson.annotations.SerializedName;

public class Results {
    @SerializedName("status")
    private String superName;


    public Results(String name) {
        this.superName = name;
    }

    public String getName() {
        return superName;
    }
}
