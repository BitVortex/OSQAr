use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let crate_root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR"));

    let shared_src = crate_root.join("..").join("c_shared_lib").join("src").join("osqar_shared.c");
    let shared_include = crate_root.join("..").join("c_shared_lib").join("include");

    println!("cargo:rerun-if-changed={}", shared_src.display());
    println!("cargo:rerun-if-changed={}", shared_include.join("osqar_shared.h").display());

    let cc = env::var("CC").unwrap_or_else(|_| "cc".to_string());
    let obj = out_dir.join("osqar_shared.o");

    let status = Command::new(cc)
        .arg("-c")
        .arg("-O2")
        .arg("-I")
        .arg(&shared_include)
        .arg(&shared_src)
        .arg("-o")
        .arg(&obj)
        .status()
        .expect("failed to invoke C compiler");

    if !status.success() {
        panic!("failed to compile shared C library object");
    }

    // Link the object file directly.
    println!("cargo:rustc-link-arg={}", obj.display());
}
