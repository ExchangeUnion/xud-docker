package base

type Config struct {
	Image       string   `usage:"Specify the image of service"`
	Dir         string   `usage:"Specify the main data directory of service"`
	ExposePorts []string `usage:"Expose service ports to your host machine"`
	Disabled    bool     `usage:"Enable/Disable service"`
}

func (t *Service) GetBranchImage(name string) string {
	// TODO get branch image
	return name
}
