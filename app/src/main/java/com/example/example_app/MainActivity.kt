package com.example.example_app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.example_app.ui.theme.Example_appTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            Example_appTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    Greeting(
                        name = "Android!",
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }
}

class FooBar {
    fun ping(): String {
        return "changed" // I've modified this line!
    }
    
    val version: Int = 1
}


class FooBar2_new {
    fun ping2(): String {
        return "pong"
    }
    
    val version2: Int = 1
}


@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Surface(color = Color.Cyan) {
        Text(
            text = "Example of $name app",
            modifier = modifier.padding(24.dp)
        )
    }
}

fun Hello_changed_2(name: String) {
  println("Hello has been changed!")
}

fun Hello_new_2(name: String) {
  println("Hello has been changed!")
}

fun Hello_new(name: String) {
  println("Now I changed this too!")
}


@Preview
@Composable
fun GreetingPreview() {
    Example_appTheme {
        Greeting("Android")
    }
}
