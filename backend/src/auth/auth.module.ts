import { Module } from '@nestjs/common';
import { AuthController } from './auth.controller.js';
import { CognitoAuthGuard } from './cognito-auth.guard.js';

@Module({
  controllers: [AuthController],
  providers: [CognitoAuthGuard],
  exports: [CognitoAuthGuard],
})
export class AuthModule {}
