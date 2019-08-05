provider "google" {
    credentials = "${file("xud-testing-8cc41bf754a6.json")}"
    project = "bustling-opus-194302"
    region = "asia-northeast1"
}

// Terraform plugin for creating random ids
resource "random_id" "instance_id" {
 byte_length = 8
}

// A single Google Cloud Engine instance
resource "google_compute_instance" "default" {
 name         = "xud-docker-${random_id.instance_id.hex}"
 machine_type = "f1-micro"
 zone         = "asia-northeast1-b"

 boot_disk {
   initialize_params {
       // https://cloud.google.com/compute/docs/images
     image = "ubuntu-os-cloud/ubuntu-1804-lts"
   }
 }

 network_interface {
   network = "default"

   access_config {
     // Include this section to give the VM an external ip address
   }
 }

 metadata_startup_script = "${file("init.sh")}"

#  metadata = {
#    ssh-keys = "reliveyy:${file("~/.ssh/id_rsa.pub")}"
#  }

}

// resource "google_compute_firewall" "default" {
//  name    = "flask-app-firewall"
//  network = "default"

// allow {
//    protocol = "tcp"
//    ports    = ["5000"]
//  }
// }

// A variable for extracting the external ip of the instance
output "ip" {
 value = "${google_compute_instance.default.network_interface.0.access_config.0.nat_ip}"
}