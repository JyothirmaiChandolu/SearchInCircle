import { Module } from '@nestjs/common';
import { AuthModule } from '../auth/auth.module.js';
import { RequirementsController } from './requirements.controller.js';
import { RequirementsService } from './requirements.service.js';

@Module({
  imports: [AuthModule],
  controllers: [RequirementsController],
  providers: [RequirementsService],
})
export class RequirementsModule {}
