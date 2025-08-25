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
        return "pong"
    }
    
    val version: Int = 1
}

class FooBar1 {
    fun ping1(): String {
        return "pong"
    }
    
    val version: Int = 1
}

class Fool{
    fun ping2(): String {
        return "pong"
    }
    
    val version: Int = 1
}

class Fool2{
    fun ping22(name: String): String {
        return "pong"
    }
    
    val version321: Int = 1
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

fun Hello(name: String) {
  println("Hello!")
}


@Preview
@Composable
fun GreetingPreview() {
    Example_appTheme {
        Greeting("Android")
    }
}
