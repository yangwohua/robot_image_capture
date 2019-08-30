#include <wiringPi.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

#define pwm_pin1 1  //定义PWM引脚 GPIO.1
#define pwm_pin2 24 //定义PWM引脚 GPIO.24
//gcc wiring_pwm.c -fpic -shared -o wiring_pwm.so -lwiringPi
void hard_pwm_init()
{
	//printf("Raspberry Pi wiringPi PWM test program\n");

	wiringPiSetup(); // wiringPi库初始化

	pinMode(pwm_pin1, PWM_OUTPUT);
	pinMode(pwm_pin2, PWM_OUTPUT);
	pwmSetRange(100);
}
void up(unsigned int speed)
{
	int clock_div;
	clock_div = speed;
	//clock_div = 512;
	printf("设置分频值：%d\n", clock_div);
	pwmSetClock(clock_div);
	pwmSetRange(1024);

	pwmWrite(pwm_pin1, speed);
	pwmWrite(pwm_pin2, 0);
}

void down(unsigned int speed)
{
	int clock_div;
	clock_div = speed;
	printf("设置分频值：%d\n", clock_div);

	pwmSetClock(clock_div);
	pwmSetRange(1024);

	pwmWrite(pwm_pin1, 0);
	pwmWrite(pwm_pin2, speed);
}
void stop()
{
	pwmWrite(pwm_pin1, 0);
	pwmWrite(pwm_pin2, 0);
}
void clear()
{
	pinMode(pwm_pin1, INPUT);
	pinMode(pwm_pin2, INPUT);
}
int main(void)
{
	hard_pwm_init(); // wiringPi库初始化

	//up(312);
	printf("sleep 5 second !!!!\n");
	//sleep(5);
	printf("sleep 5 second over\n");
	//stop();
	//sleep(2);
	down(112);
	//while (1);
	sleep(5);
	clear();
	return 0;
}
