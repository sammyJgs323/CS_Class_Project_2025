/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
	/* EEE3095S
	 * CS Class Project 2025
	 * PFFTAH001, SMLJOS008
	 *
	 * */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <string.h>
#include <stdbool.h>
#include <stdio.h>
//for the STM32F4
#include "stm32f4xx.h"
#include "stm32f4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
//UART handle for USART1
UART_HandleTypeDef huart1;

//max length for each access code
#define MAX_LEN 100

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART1_UART_Init();
  /* USER CODE BEGIN 2 */


  //buffer for three access codes (each up to 100 chars + null terminator)
  char accessCodes[3][MAX_LEN + 1];
  memset(accessCodes, 0, sizeof(accessCodes));  // initialize all codes as empty

  //connection state, true after connect false after disconnect
  bool connected = false;

  //buffer for incoming UART data/ commands
  char dataBuff[128];

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	    //receive a line (command) from UART
	    char c;
	    uint16_t i = 0;
	    // Read characters one by one until newline ('\n') is received
	    do {
	      if (HAL_UART_Receive(&huart1, (uint8_t*)&c, 1, HAL_MAX_DELAY) != HAL_OK) {
	        Error_Handler();  // In case of UART error, halt (could also continue to next loop)
	      }
	      if (c == '\r') {
	    	  // skip carriage return if present
	        continue;
	      }
	      if (c == '\n') {
	    	  // newline indicates end of command
	        break;
	      }
	      if (i < sizeof(dataBuff) - 1) {
	    	  // append character to buffer if space allows
	        dataBuff[i++] = c;
	      } else {
	        // buffer overflow if line too long then truncate and break
	        dataBuff[i] = '\0';
	        break;
	      }
	    } while (1);
	    // null-terminate the received string
	    dataBuff[i] = '\0';

	    //parse and handle the command in dataBuff
	    if (strcmp(dataBuff, "CONNECT") == 0) {
	      // CONNECT command: establish connection
	      connected = true;
	      const char *resp = "OK\r\n";
	      HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	      //ensures register is cleared
	      __HAL_UART_FLUSH_DRREGISTER(&huart1);
	    }
	    else if (!connected) {
	      // if not connected yet, only CONNECT is valid and respond with error for any other command
	      const char *resp = "ERROR\r\n";
	      HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	      __HAL_UART_FLUSH_DRREGISTER(&huart1);
	    }
	    else if (strcmp(dataBuff, "DISCONNECT") == 0) {
	      // DISCONNECT command: end session
	      connected = false;
	      const char *resp = "OK\r\n";
	      HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	      __HAL_UART_FLUSH_DRREGISTER(&huart1);
	      // after disconnect the device stays running and can accept a new CONNECT
	    }
	    else if (strncmp(dataBuff, "GET_CODE_", 9) == 0) {
	      // GET_CODE_n command: retrieve a code if it exists
	      // expect exactly one digit (1-3) after "GET_CODE_"
	    	// the character representing code index
	      char codeIndexChar = dataBuff[9];

	      if ((codeIndexChar >= '1' && codeIndexChar <= '3') && dataBuff[10] == '\0') {
	    	  // convert '1','2','3' to 0,1,2
	        int idx = codeIndexChar - '1';

	        if (accessCodes[idx][0] != '\0') {
	          // if code exists send it back prefixed with "CODE:"
	          char codeBuff[128];
	          snprintf(codeBuff, sizeof(codeBuff), "CODE:%s\n", accessCodes[idx]);
	          HAL_UART_Transmit(&huart1, (uint8_t*)codeBuff, strlen(codeBuff), HAL_MAX_DELAY);
	          __HAL_UART_FLUSH_DRREGISTER(&huart1);
	        } else {
	          // if code not set respond with NOT_FOUND
	          const char *resp = "NOT_FOUND\r\n";
	          HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	          __HAL_UART_FLUSH_DRREGISTER(&huart1);
	        }
	      } else {
	        // error in GET_CODE command such as invalid index or extra characters
	        const char *resp = "ERROR\r\n";
	        HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	        __HAL_UART_FLUSH_DRREGISTER(&huart1);
	      }
	    }
	    else if (strncmp(dataBuff, "SET_CODE_", 9) == 0) {
	      // SET_CODE_n:value command: store a new code value
	    	// the character representing code index
	      char codeIndexChar = dataBuff[9];

	      if ((codeIndexChar >= '1' && codeIndexChar <= '3') && dataBuff[10] == ':') {
	    	  // target index 0-2
	        int idx = codeIndexChar - '1';
	        // pointer to the code value after the SET_CODE_n prefix
	        char *codeValue = &dataBuff[11];
	        // save the new code up to MAX_Len characters
	        if (strlen(codeValue) <= MAX_LEN) {
	          strcpy(accessCodes[idx], codeValue);
	        } else {
	          strncpy(accessCodes[idx], codeValue, MAX_LEN);
	          // ensure termination if truncated
	          accessCodes[idx][MAX_LEN] = '\0';
	        }
	        // respond to confirm the code is saved
	        const char *resp = "SAVED\r\n";
	        HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	        __HAL_UART_FLUSH_DRREGISTER(&huart1);
	      } else {
	        // error in SET_CODE command such as missing index or colon
	        const char *resp = "ERROR\r\n";
	        HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	        __HAL_UART_FLUSH_DRREGISTER(&huart1);
	      }
	    }
	    else {
	      // unknown command received respond with generic error
	      const char *resp = "ERROR\r\n";
	      HAL_UART_Transmit(&huart1, (uint8_t*)resp, strlen(resp), HAL_MAX_DELAY);
	      __HAL_UART_FLUSH_DRREGISTER(&huart1);
	    }

	    // loop back to wait for the next command line
	  }

  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  //RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 16;
  RCC_OscInitStruct.PLL.PLLN = 336;
  // 16 MHz * 336 / 4 = 84 MHz
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
  RCC_OscInitStruct.PLL.PLLQ = 7;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  //system clock= PLL 84MHz
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  //HCLK=84 MHz
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  //APB1=42 MHz
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  //APB2=84 MHz
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{

  /* USER CODE BEGIN USART1_Init 0 */
	/* Enable UART and GPIO clocks */
	 __HAL_RCC_USART1_CLK_ENABLE();
	 __HAL_RCC_GPIOA_CLK_ENABLE();

	  /* Configure PA9  and PA10 as alternate function UART pins */
	  GPIO_InitTypeDef GPIO_InitStruct = {0};
	  GPIO_InitStruct.Pin = GPIO_PIN_9 | GPIO_PIN_10;
	  // push-pull alternate function
	  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
	  // no pull-up or pull-down resistors
	  GPIO_InitStruct.Pull = GPIO_NOPULL;
	  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
	  // AF7 for USART1 pins
	  GPIO_InitStruct.Alternate = GPIO_AF7_USART1;
	  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /* USER CODE END USART1_Init 0 */

  /* USER CODE BEGIN USART1_Init 1 */

  /* USER CODE END USART1_Init 1 */
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART1_Init 2 */

  /* USER CODE END USART1_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0|GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_3
                          |GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7, GPIO_PIN_RESET);

  /*Configure GPIO pins : PB0 PB1 PB2 PB3
                           PB4 PB5 PB6 PB7 */
  GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_3
                          |GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
