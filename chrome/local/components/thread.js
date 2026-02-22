function Task(name, delay, exec) {
	// overwrite this function
	this.exec = exec || function (task, resolve) { resolve(); };
	this.name = name;
	this.delay = delay || 0;
}

class Thread {
	constructor(intervalTime = 300) {
		this.tasks = [];
		this.runing = false;
		this.curTaskBeginTime = 0;
		this.intervalTime = intervalTime || 300;
	}

	start(intervalTime) {
		if (this.runing) {
			return;
		}
		this.curTaskBeginTime = Date.now();
		this.intervalTime = intervalTime || 500;
		this.runing = true;
		this._wait();
	}
	
	_wait() {
		let rr = () => this._run();
		setTimeout(rr, this.intervalTime);
	}

	_run() {
		if (! this.runing) {
			return; // stop
		}
		if (this.tasks.length == 0) {
			this._wait();
			return;
		}
		let topTask = this.tasks[0];
		let diffTime = Date.now() - this.curTaskBeginTime;
		if (diffTime < topTask.delay) {
			// console.log('Wait...');
			// wait
			this._wait();
			return;
		}
		let curTask = this.tasks.shift();
		curTask.exec(curTask, () => this._resolve());
	}

	_resolve() {
		this.curTaskBeginTime = Date.now();
		this._run(); // run next task
	}
	
	stop() {
		this.runing = false;
		this.curTaskBeginTime = 0;
	}

	// exec: function(resolve, reject) 
	// when finish call resolve() or reject()
	addTask(task) {
		this.tasks.push(task);
	}

	insertTask(idx, task) {
		this.tasks.splice(idx, 0, task);
	}

	addUniqueTask(uniqueId, task) {
		if (! task) {
			return;
		}
		for (let i = 0; i < this.tasks.length; i++) {
			let tk = this.tasks[i];
			if (tk._UNIQUE_ID && tk._UNIQUE_ID == uniqueId) {
				return;
			}
		}
		if (uniqueId != null) {
			task._UNIQUE_ID = uniqueId;
		}
		
		this.tasks.push(task);
	}

	removeUniqueTask(uniqueId) {
		if (uniqueId == undefined || uniqueId == null || uniqueId == '') {
			return;
		}
		for (let i = 0; i < this.tasks.length; i++) {
			if (this.tasks[i]._UNIQUE_ID == uniqueId) {
				this.tasks.splice(i, 1);
				break;
			}
		}
	}
}


export {
	Thread, Task
}